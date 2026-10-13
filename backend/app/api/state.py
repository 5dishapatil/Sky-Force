"""Application runtime state container and dependencies."""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import select

from app.core.config import Settings, get_settings
from app.db import models as m
from app.db.session import get_sessionmaker
from app.services.features.congestion import Thresholds
from app.services.geospatial.grid import Grid, grid_from_settings
from app.services.models.registry import LoadedModel, load_active, read_metadata
from app.services.routing.graph import RouteGraph, build_graph
from app.services.routing.planner import RoutePlanner
from app.services.routing.providers import ContextBuilder, DataStore


@dataclass
class AppState:
    settings: Settings
    grid: Grid
    graph: RouteGraph
    planner: RoutePlanner
    store: DataStore
    context_builder: ContextBuilder
    congestion_model: LoadedModel | None
    eta_model: LoadedModel | None
    thresholds: Thresholds | None


_state: AppState | None = None


def init_app_state() -> AppState:
    global _state
    s = get_settings()
    grid = grid_from_settings(s)
    session_factory = get_sessionmaker(s.database_url)

    # 1. Load airports, waypoints, edges from DB
    with session_factory() as session:
        airports_raw = [
            {
                "node_id": a.node_id,
                "name": a.name,
                "latitude": a.latitude,
                "longitude": a.longitude,
                "iata": a.iata,
                "country": a.country,
                "source": a.source,
            }
            for a in session.scalars(select(m.Airport)).all()
        ]
        waypoints_raw = [
            {
                "node_id": w.node_id,
                "name": w.name,
                "latitude": w.latitude,
                "longitude": w.longitude,
                "source": w.source,
            }
            for w in session.scalars(select(m.Waypoint)).all()
        ]
        edges_raw = [
            {
                "edge_id": e.edge_id,
                "source_node": e.source_node,
                "target_node": e.target_node,
                "distance_km": e.distance_km,
                "bearing_deg": e.bearing_deg,
                "is_synthetic": e.is_synthetic,
                "provenance": e.provenance,
            }
            for e in session.scalars(select(m.RouteEdge)).all()
        ]

    graph = build_graph(airports_raw, waypoints_raw, edges_raw, s.heuristic_cruise_speed_kmh)
    planner = RoutePlanner(graph)

    # 2. Load processed frames for ContextBuilder if present
    p_dir = s.data_dir / "processed"
    s_dir = s.data_dir / "synthetic"
    
    agg = pd.DataFrame()
    weather = pd.DataFrame()
    thresholds: Thresholds | None = None

    if (p_dir / "congestion_agg.parquet").exists():
        agg = pd.read_parquet(p_dir / "congestion_agg.parquet")
    if (s_dir / "weather_synthetic.parquet").exists():
        weather = pd.read_parquet(s_dir / "weather_synthetic.parquet")
    if (p_dir / "congestion_thresholds.json").exists():
        th_data = json.loads((p_dir / "congestion_thresholds.json").read_text())
        thresholds = Thresholds(th_data["low_max"], th_data["medium_max"], th_data["method"])

    corridor = sorted({
        c for u, v, _ in graph.g.edges(data=True)
        for c in grid.cells_along(*graph.pos(u), *graph.pos(v))
    })
    airport_nodes = {a["node_id"] for a in airports_raw}

    store = DataStore(
        agg=agg,
        weather=weather,
        corridor_cells=corridor,
        airports=airport_nodes,
        dataset_id=s.demo_dataset_id,
        weather_source_label="Synthetic Hourly Field (corridor grid)",
    )

    # 3. Models
    cm: LoadedModel | None = None
    em: LoadedModel | None = None
    try:
        cm = load_active("congestion", s.artifacts_dir)
    except Exception:
        cm = None

    try:
        em = load_active("eta", s.artifacts_dir)
    except Exception:
        em = None

    builder = ContextBuilder(
        rg=graph,
        grid=grid,
        store=store,
        window_min=s.window_minutes,
        cruise_kmh=s.heuristic_cruise_speed_kmh,
        congestion_model=cm,
        eta_model=em,
        thresholds=thresholds,
    )

    _state = AppState(
        settings=s,
        grid=grid,
        graph=graph,
        planner=planner,
        store=store,
        context_builder=builder,
        congestion_model=cm,
        eta_model=em,
        thresholds=thresholds,
    )
    return _state


def get_state() -> AppState:
    global _state
    if _state is None:
        return init_app_state()
    return _state
