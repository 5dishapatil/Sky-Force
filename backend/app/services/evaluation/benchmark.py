"""Routing Evaluation and Scientific Experiment Runner.

Compares candidate routing objectives across defined baseline and disrupted
scenarios under identical graph topologies. Records trade-offs honestly:
distance, travel time, composite score, closed edges avoided, congestion/weather
exposure, and planning latency.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.db import models as m
from app.services.routing.context import RoutingContext
from app.services.routing.cost_model import CostWeights
from app.services.routing.planner import RoutePlanner
from app.services.scenario_engine.events import apply_events

BENCHMARK_OBJECTIVES = [
    ("distance", "Shortest-distance baseline", CostWeights.preset("distance")),
    ("fastest", "Fastest candidate", CostWeights.preset("fastest")),
    ("weather", "Weather-aware", CostWeights.preset("weather")),
    ("congestion", "Congestion-aware", CostWeights.preset("congestion")),
    ("balanced", "Composite multi-factor", CostWeights.preset("balanced")),
]


def run_routing_benchmark(
    planner: RoutePlanner,
    base_ctx: RoutingContext,
    scenarios: list[dict[str, Any]],
    od_pairs: list[tuple[str, str]],
    algorithm: str = "dijkstra",
    grid: Any = None,
) -> dict[str, Any]:
    """Runs a multi-scenario, multi-objective comparative routing experiment."""
    results: list[dict[str, Any]] = []
    t_start = time.perf_counter()

    for sc in scenarios:
        sc_id = sc["id"]
        sc_name = sc["name"]
        events = sc.get("events", [])
        
        # Apply scenario events non-mutatingly
        ctx = apply_events(base_ctx, events, planner.rg, grid) if grid else base_ctx.copy()

        for origin, destination in od_pairs:
            for obj_key, obj_label, weights in BENCHMARK_OBJECTIVES:
                t0 = time.perf_counter()
                res = planner.plan(origin, destination, weights, ctx, algorithm, label=obj_key)
                latency_ms = (time.perf_counter() - t0) * 1000.0

                if res.get("found"):
                    totals = res["totals"]
                    row = {
                        "scenario_id": sc_id,
                        "scenario_name": sc_name,
                        "origin": origin,
                        "destination": destination,
                        "algorithm": algorithm,
                        "objective": obj_key,
                        "objective_label": obj_label,
                        "route_found": True,
                        "route_id": res["route_id"],
                        "path": res["path"],
                        "route_distance_km": totals["distance_km"],
                        "estimated_time_min": totals["estimated_time_min"],
                        "weather_penalty": totals["weather_exposure_km"],
                        "congestion_penalty": totals["congestion_exposure_km"],
                        "total_composite_score": totals["composite_score"],
                        "replanning_latency_ms": round(latency_ms, 2),
                        "closed_edges_in_route": totals["closed_edges_in_route"],
                        "nodes_expanded": res["search"]["nodes_expanded"],
                    }
                else:
                    row = {
                        "scenario_id": sc_id,
                        "scenario_name": sc_name,
                        "origin": origin,
                        "destination": destination,
                        "algorithm": algorithm,
                        "objective": obj_key,
                        "objective_label": obj_label,
                        "route_found": False,
                        "route_id": None,
                        "path": None,
                        "route_distance_km": None,
                        "estimated_time_min": None,
                        "weather_penalty": None,
                        "congestion_penalty": None,
                        "total_composite_score": None,
                        "replanning_latency_ms": round(latency_ms, 2),
                        "closed_edges_in_route": None,
                        "nodes_expanded": res["search"]["nodes_expanded"],
                        "failure_reason": res.get("reason"),
                    }
                results.append(row)

    total_s = time.perf_counter() - t_start
    return {
        "experiment_id": f"EXP-{int(time.time())}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "total_evaluations": len(results),
        "total_duration_s": round(total_s, 2),
        "results": results,
    }


def persist_experiment_run(session: Session, exp: dict[str, Any]) -> m.ExperimentRun:
    """Saves benchmark results to the database."""
    run = m.ExperimentRun(
        id=exp["experiment_id"],
        kind="routing_benchmark",
        status="completed",
        config={
            "evaluations": exp["total_evaluations"],
            "duration_s": exp["total_duration_s"],
        },
        summary={
            "total_evaluations": exp["total_evaluations"],
            "success_rate": round(sum(1 for r in exp["results"] if r["route_found"]) / len(exp["results"]), 3) if exp["results"] else 0,
        },
    )
    session.add(run)
    session.flush()

    for r in exp["results"]:
        eval_record = m.RouteEvaluation(
            experiment_id=run.id,
            scenario_id=r["scenario_id"],
            origin=r["origin"],
            destination=r["destination"],
            algorithm=r["algorithm"],
            objective=r["objective"],
            route_found=r["route_found"],
            route_distance_km=r["route_distance_km"],
            estimated_time_min=r["estimated_time_min"],
            weather_penalty=r["weather_penalty"],
            congestion_penalty=r["congestion_penalty"],
            total_composite_score=r["total_composite_score"],
            replanning_latency_ms=r["replanning_latency_ms"],
            closed_edges_in_route=r["closed_edges_in_route"],
            nodes_expanded=r["nodes_expanded"],
            path=r["path"],
        )
        session.add(eval_record)

    session.commit()
    return run
