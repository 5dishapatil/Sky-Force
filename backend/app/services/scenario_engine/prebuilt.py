"""Prebuilt, deterministic demonstration scenarios (all labelled SIMULATED / generated_demo).

The corridor used by the scenarios is the distance-shortest path VIDP -> VABB
(Delhi -> Mumbai) on the synthetic graph, computed at seeding time.
"""
from __future__ import annotations

import copy
from datetime import timedelta
from typing import Any

import networkx as nx
import pandas as pd
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.db import models as m
from app.services.geospatial.geo import destination_point

DEMO_ORIGIN, DEMO_DEST = "VIDP", "VABB"


def _circle(lat: float, lon: float, radius_km: float, n: int = 18) -> list[list[float]]:
    return [list(map(lambda x: round(x, 4), destination_point(lat, lon, 360 * i / n, radius_km))) for i in range(n)]


def build_prebuilt(edges: pd.DataFrame, pos: dict[str, tuple[float, float]], scenario_time) -> list[dict[str, Any]]:  # noqa: ANN001
    g = nx.DiGraph()
    for e in edges.itertuples():
        g.add_edge(e.source_node, e.target_node, w=e.distance_km)
    gen = nx.shortest_simple_paths(g, DEMO_ORIGIN, DEMO_DEST, weight="w")
    p1 = next(gen)
    mid = len(p1) // 2
    mid_edges = [f"{p1[mid - 1]}->{p1[mid]}", f"{p1[mid]}->{p1[mid - 1]}"]
    corridor_edges = [f"{u}->{v}" for u, v in zip(p1[:-1], p1[1:])]
    # alternate path once the middle edge is closed (for the combined scenario)
    g2 = g.copy()
    g2.remove_edge(p1[mid - 1], p1[mid])
    p2 = nx.shortest_path(g2, DEMO_ORIGIN, DEMO_DEST, weight="w")
    alt_edges = [f"{u}->{v}" for u, v in zip(p2[:-1], p2[1:]) if f"{u}->{v}" not in corridor_edges]
    mlat = (pos[p1[mid - 1]][0] + pos[p1[mid]][0]) / 2
    mlon = (pos[p1[mid - 1]][1] + pos[p1[mid]][1]) / 2
    t0, t1 = scenario_time - timedelta(hours=3), scenario_time + timedelta(hours=5)

    def ev(eid: str, name: str, et: str, scope: dict, sev: float, desc: str) -> dict:
        return {"id": eid, "name": name, "event_type": et, "scope": scope, "severity": sev, "description": desc,
                "start_time_utc": t0, "end_time_utc": t1, "enabled": True, "source_status": "generated_demo"}

    wp_lat, wp_lon = pos[p1[1]] if len(p1) > 2 else (mlat, mlon)
    return [
        {"id": "clear", "name": "1. Clear conditions", "description": "No simulated events. Baseline network state.", "events": []},
        {"id": "corridor-congestion", "name": "2. High congestion in the Delhi–Mumbai corridor",
         "description": "SIMULATED traffic-density surge on every segment of the direct VIDP→VABB corridor.",
         "events": [ev("ev-cong-corridor", "Simulated corridor traffic surge", "traffic_surge",
                       {"edge_ids": corridor_edges}, 0.9, "Adds +0.9 to the congestion score of corridor segments.")]},
        {"id": "corridor-closure", "name": "3. Temporary corridor closure",
         "description": f"SIMULATED closure of segment {mid_edges[0]} (both directions) on the direct corridor.",
         "events": [ev("ev-close-mid", "Simulated temporary segment closure", "edge_closure",
                       {"edge_ids": mid_edges}, 1.0, "Hard closure; segments are removed from route search.")]},
        {"id": "weather-zone", "name": "4. Increased weather penalty around central corridor",
         "description": "SIMULATED weather-penalty zone (radius 220 km) around the corridor mid-point.",
         "events": [ev("ev-wx-zone", "Simulated convective weather zone", "weather_penalty_zone",
                       {"polygon": _circle(mlat, mlon, 220)}, 0.85, "Adds +0.85 weather severity to intersecting segments.")]},
        {"id": "combined", "name": "5. Combined closure + congestion on the alternate",
         "description": "SIMULATED closure of the corridor mid-segment AND a surge on the best alternate path, plus stale data.",
         "events": [
             ev("ev-comb-close", "Simulated closure (combined)", "edge_closure", {"edge_ids": mid_edges}, 1.0, "Hard closure."),
             ev("ev-comb-surge", "Simulated surge on alternate", "traffic_surge", {"edge_ids": alt_edges or corridor_edges}, 0.8,
                "Adds +0.8 congestion on the alternate path."),
             ev("ev-comb-stale", "Simulated stale surveillance feed", "stale_data", {"edge_ids": alt_edges[:2] or corridor_edges[:2]},
                0.5, "Raises uncertainty on two segments."),
         ]},
        {"id": "restricted-area", "name": "6. Synthetic restricted area",
         "description": "SIMULATED restricted polygon (radius 120 km) near the first corridor waypoint. Not a real NOTAM.",
         "events": [ev("ev-restricted", "Simulated restricted area", "restricted_polygon",
                       {"polygon": _circle(wp_lat, wp_lon, 120)}, 1.0, "Every segment intersecting the polygon is closed.")]},
    ]


def seed_prebuilt_scenarios(session: Session, settings, edges: pd.DataFrame, pos: dict[str, tuple[float, float]]) -> int:  # noqa: ANN001
    session.execute(delete(m.Scenario).where(m.Scenario.is_prebuilt.is_(True)))
    session.flush()
    specs = build_prebuilt(edges, pos, settings.default_scenario_time_utc)
    for sp in specs:
        sc = m.Scenario(id=sp["id"], name=sp["name"], description=sp["description"], is_prebuilt=True,
                        is_active=False, seed=settings.demo_seed, scenario_time_utc=settings.default_scenario_time_utc)
        for e in sp["events"]:
            orig = copy.deepcopy({k: (v.isoformat() if hasattr(v, "isoformat") else v) for k, v in e.items()})
            sc.events.append(m.ScenarioEvent(original=orig, **e))
        session.add(sc)
    return len(specs)


def prebuilt_ids(session: Session) -> list[str]:
    return list(session.scalars(select(m.Scenario.id).where(m.Scenario.is_prebuilt.is_(True))))
