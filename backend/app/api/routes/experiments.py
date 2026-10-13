"""Scientific routing benchmark and experiment execution routes."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.state import get_state
from app.db import models as m
from app.db.session import get_db
from app.services.evaluation.benchmark import persist_experiment_run, run_routing_benchmark

router = APIRouter(prefix="/experiments", tags=["Experiments & Benchmarks"])


class ExperimentRunRequest(BaseModel):
    od_pairs: list[list[str]] = Field(
        default=[["VIDP", "VABB"], ["VABB", "VIDP"]],
        description="List of [origin, destination] ICAO code pairs",
    )
    scenario_ids: list[str] = Field(
        default=["clear", "corridor-congestion", "corridor-closure"],
        description="Scenario IDs to evaluate across",
    )
    algorithm: str = Field(default="dijkstra", description="Search algorithm ('dijkstra' or 'astar')")


@router.post("/run")
def execute_routing_benchmark(
    req: ExperimentRunRequest,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    state = get_state()
    base_ctx = state.context_builder.base_context(state.settings.default_scenario_time_utc)

    # Resolve scenarios from database
    sc_rows = db.scalars(
        select(m.Scenario).where(m.Scenario.id.in_(req.scenario_ids))
    ).all()

    if not sc_rows:
        # Fall back to all scenarios in DB if specific ones not matched
        sc_rows = db.scalars(select(m.Scenario).limit(5)).all()

    selected_scenarios: list[dict[str, Any]] = [
        {
            "id": sc.id,
            "name": sc.name,
            "events": [
                {
                    "id": e.id,
                    "name": e.name,
                    "event_type": e.event_type,
                    "start_time_utc": e.start_time_utc,
                    "end_time_utc": e.end_time_utc,
                    "scope": e.scope or {},
                    "severity": e.severity,
                    "description": e.description or "",
                    "enabled": e.enabled,
                }
                for e in sc.events
                if e.enabled
            ],
        }
        for sc in sc_rows
    ]

    if not selected_scenarios:
        raise HTTPException(
            status_code=400,
            detail="No scenarios found in database.",
        )

    od_tuples = [(pair[0].strip().upper(), pair[1].strip().upper()) for pair in req.od_pairs if len(pair) == 2]
    if not od_tuples:
        raise HTTPException(status_code=400, detail="At least one valid [origin, destination] pair is required.")

    # Execute benchmark
    benchmark_res = run_routing_benchmark(
        planner=state.planner,
        base_ctx=base_ctx,
        scenarios=selected_scenarios,
        od_pairs=od_tuples,
        algorithm=req.algorithm,
        grid=state.grid,
    )

    # Persist in DB
    run_record = persist_experiment_run(db, benchmark_res)

    return {
        "experiment_id": run_record.id,
        "status": run_record.status,
        "total_evaluations": benchmark_res["total_evaluations"],
        "total_duration_s": benchmark_res["total_duration_s"],
        "results": benchmark_res["results"],
        "summary": run_record.summary,
    }


@router.get("")
def list_experiment_runs(
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    runs = db.scalars(
        select(m.ExperimentRun)
        .order_by(m.ExperimentRun.created_at.desc())
        .limit(limit)
    ).all()

    return [
        {
            "id": r.id,
            "kind": r.kind,
            "status": r.status,
            "config": r.config,
            "summary": r.summary,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in runs
    ]


@router.get("/{experiment_id}")
def get_experiment_details(
    experiment_id: str,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    run = db.get(m.ExperimentRun, experiment_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Experiment '{experiment_id}' not found")

    evals = db.scalars(
        select(m.RouteEvaluation)
        .where(m.RouteEvaluation.experiment_id == experiment_id)
    ).all()

    return {
        "id": run.id,
        "kind": run.kind,
        "status": run.status,
        "config": run.config,
        "summary": run.summary,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "evaluations": [
            {
                "id": e.id,
                "scenario_id": e.scenario_id,
                "origin": e.origin,
                "destination": e.destination,
                "algorithm": e.algorithm,
                "objective": e.objective,
                "route_found": e.route_found,
                "route_distance_km": e.route_distance_km,
                "estimated_time_min": e.estimated_time_min,
                "weather_penalty": e.weather_penalty,
                "congestion_penalty": e.congestion_penalty,
                "total_composite_score": e.total_composite_score,
                "replanning_latency_ms": e.replanning_latency_ms,
                "closed_edges_in_route": e.closed_edges_in_route,
                "nodes_expanded": e.nodes_expanded,
                "path": e.path,
            }
            for e in evals
        ],
    }
