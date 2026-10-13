"""Scenario management and dynamic rerouting endpoints."""
from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.state import get_state
from app.core.errors import NotFoundError
from app.db import models as m
from app.db.session import get_db
from app.schemas.scenarios import (
    CreateScenarioInput,
    DynamicRerouteRequest,
    DynamicRerouteResponse,
    ScenarioEventItem,
    ScenarioItem,
)
from app.services.routing.cost_model import CostWeights
from app.services.routing.explain import explain_route
from app.services.routing.planner import OBJECTIVE_NAMES, closed_edges_on_unconstrained
from app.services.scenario_engine.events import apply_events, validate_event

router = APIRouter(prefix="/scenarios", tags=["Scenario Studio"])


def _scenario_to_dict(sc: m.Scenario) -> ScenarioItem:
    return ScenarioItem(
        id=sc.id,
        name=sc.name,
        description=sc.description or "",
        is_prebuilt=sc.is_prebuilt,
        is_active=sc.is_active,
        seed=sc.seed,
        scenario_time_utc=sc.scenario_time_utc,
        created_at=sc.created_at,
        updated_at=sc.updated_at,
        events=[
            ScenarioEventItem(
                id=e.id,
                name=e.name,
                description=e.description or "",
                event_type=e.event_type,
                start_time_utc=e.start_time_utc,
                end_time_utc=e.end_time_utc,
                enabled=e.enabled,
                scope=e.scope or {},
                severity=e.severity,
                source_status=e.source_status,
            )
            for e in sc.events
        ],
    )


@router.get("", response_model=list[ScenarioItem])
def list_scenarios(db: Session = Depends(get_db)) -> list[ScenarioItem]:
    scenarios = db.scalars(select(m.Scenario).order_by(m.Scenario.id.asc())).all()
    return [_scenario_to_dict(sc) for sc in scenarios]


@router.get("/{scenario_id}", response_model=ScenarioItem)
def get_scenario(scenario_id: str, db: Session = Depends(get_db)) -> ScenarioItem:
    sc = db.scalar(select(m.Scenario).where(m.Scenario.id == scenario_id))
    if not sc:
        raise NotFoundError(f"Scenario '{scenario_id}' not found", code="SCENARIO_NOT_FOUND")
    return _scenario_to_dict(sc)


@router.post("", response_model=ScenarioItem)
def create_scenario(req: CreateScenarioInput, db: Session = Depends(get_db)) -> ScenarioItem:
    state = get_state()
    sc_id = f"custom-{uuid.uuid4().hex[:8]}"
    t = req.scenario_time_utc or state.settings.default_scenario_time_utc
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)

    sc = m.Scenario(
        id=sc_id,
        name=req.name,
        description=req.description,
        is_prebuilt=False,
        is_active=False,
        seed=state.settings.demo_seed,
        scenario_time_utc=t,
    )

    for ev_in in req.events:
        ev_dict = {
            "id": f"ev-{uuid.uuid4().hex[:8]}",
            "name": ev_in.name,
            "description": ev_in.description,
            "event_type": ev_in.event_type,
            "start_time_utc": ev_in.start_time_utc,
            "end_time_utc": ev_in.end_time_utc,
            "enabled": ev_in.enabled,
            "scope": ev_in.scope,
            "severity": ev_in.severity,
            "source_status": ev_in.source_status,
        }
        validate_event(ev_dict, state.graph)
        orig = copy.deepcopy({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in ev_dict.items()})
        sc.events.append(m.ScenarioEvent(original=orig, **ev_dict))

    db.add(sc)
    db.commit()
    db.refresh(sc)
    return _scenario_to_dict(sc)


@router.post("/{scenario_id}/activate", response_model=ScenarioItem)
def activate_scenario(scenario_id: str, db: Session = Depends(get_db)) -> ScenarioItem:
    sc = db.scalar(select(m.Scenario).where(m.Scenario.id == scenario_id))
    if not sc:
        raise NotFoundError(f"Scenario '{scenario_id}' not found")

    # Deactivate all others
    db.execute(update(m.Scenario).values(is_active=False))
    sc.is_active = True
    sc.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sc)
    return _scenario_to_dict(sc)


@router.post("/{scenario_id}/reset", response_model=ScenarioItem)
def reset_scenario(scenario_id: str, db: Session = Depends(get_db)) -> ScenarioItem:
    sc = db.scalar(select(m.Scenario).where(m.Scenario.id == scenario_id))
    if not sc:
        raise NotFoundError(f"Scenario '{scenario_id}' not found")

    # Restore events from original snapshot
    for ev in sc.events:
        if ev.original:
            ev.name = ev.original.get("name", ev.name)
            ev.event_type = ev.original.get("event_type", ev.event_type)
            ev.enabled = ev.original.get("enabled", True)
            ev.severity = float(ev.original.get("severity", 1.0))
            ev.scope = ev.original.get("scope", {})

    sc.is_active = False
    sc.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(sc)
    return _scenario_to_dict(sc)


@router.post("/reroute", response_model=DynamicRerouteResponse)
def dynamic_reroute(req: DynamicRerouteRequest, db: Session = Depends(get_db)) -> DynamicRerouteResponse:
    state = get_state()
    sc = db.scalar(select(m.Scenario).where(m.Scenario.id == req.scenario_id))
    if not sc:
        raise NotFoundError(f"Scenario '{req.scenario_id}' not found")

    t = sc.scenario_time_utc or state.settings.default_scenario_time_utc
    base_ctx = state.context_builder.base_context(t)
    w = CostWeights.preset(req.objective if req.objective in ["distance", "fastest", "weather", "congestion", "balanced"] else "balanced")

    # 1. Baseline Route (unperturbed)
    base_res = state.planner.plan(req.origin, req.destination, w, base_ctx, req.algorithm, label="baseline")

    # 2. Perturbed Route with scenario events
    ev_dicts = [
        {
            "id": e.id,
            "name": e.name,
            "event_type": e.event_type,
            "start_time_utc": e.start_time_utc,
            "end_time_utc": e.end_time_utc,
            "enabled": e.enabled,
            "scope": e.scope,
            "severity": e.severity,
            "source_status": e.source_status,
        }
        for e in sc.events
    ]
    sc_ctx = apply_events(base_ctx, ev_dicts, state.graph, state.grid)
    rerouted_res = state.planner.plan(req.origin, req.destination, w, sc_ctx, req.algorithm, label="rerouted")

    # Compute deltas
    delta = {}
    if base_res.get("found") and rerouted_res.get("found"):
        b_tot = base_res["totals"]
        r_tot = rerouted_res["totals"]
        delta = {
            "path_changed": base_res["path"] != rerouted_res["path"],
            "distance_km_delta": round(r_tot["distance_km"] - b_tot["distance_km"], 2),
            "estimated_time_min_delta": round(r_tot["estimated_time_min"] - b_tot["estimated_time_min"], 2),
            "weather_penalty_delta": round(r_tot["weather_exposure_km"] - b_tot["weather_exposure_km"], 2),
            "congestion_penalty_delta": round(r_tot["congestion_exposure_km"] - b_tot["congestion_exposure_km"], 2),
            "composite_score_delta": round(r_tot["composite_score"] - b_tot["composite_score"], 4),
        }

    closed_avoided = closed_edges_on_unconstrained(state.planner, req.origin, req.destination, sc_ctx, w, req.algorithm)
    expl = explain_route(
        route=rerouted_res,
        baseline=base_res if base_res.get("found") else None,
        ctx=sc_ctx,
        objective_name=OBJECTIVE_NAMES.get(req.objective, req.objective),
        closed_on_direct=closed_avoided,
    )

    return DynamicRerouteResponse(
        scenario_id=sc.id,
        scenario_name=sc.name,
        origin=req.origin,
        destination=req.destination,
        baseline_route=base_res,
        rerouted_route=rerouted_res,
        delta=delta,
        explanation=expl,
        affected_events=sc_ctx.active_events,
    )
