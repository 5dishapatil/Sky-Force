"""Scenario events and their (pure) application to a routing context.

Event types & scope schema
--------------------------
edge_closure          {"edge_ids": [...]}                 hard closure of edges
restricted_polygon    {"polygon": [[lat, lon], ...]}      hard closure of every edge whose densified
                                                          great-circle geometry intersects the polygon
traffic_surge         {"edge_ids": [...]} | {"cell_ids": [...]}  congestion score += severity (clip 1)
weather_penalty_zone  {"polygon": [[lat, lon], ...]}      weather severity += severity (clip 1)
eta_increase          {"edge_ids": [...]}                 time *= (1 + severity)
stale_data            {"edge_ids": [...]} | {"polygon": ...}  uncertainty += severity, inputs flagged stale

An event applies when ``enabled`` and ``start <= scenario_time < end``.
Geometry tests use planar lon/lat geometry (Shapely) on densified great-circle
samples - adequate for the regional demo; documented limitation.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from shapely.geometry import LineString, Polygon

from app.core.errors import ValidationFailed
from app.services.geospatial.grid import Grid
from app.services.routing.context import RoutingContext
from app.services.routing.graph import RouteGraph

EVENT_TYPES = {"edge_closure", "restricted_polygon", "traffic_surge", "weather_penalty_zone", "eta_increase", "stale_data"}
SOURCE_STATUSES = {"verified", "historical", "user_defined_simulation", "generated_demo"}


def validate_event(ev: dict[str, Any], rg: RouteGraph) -> None:
    et = ev.get("event_type")
    if et not in EVENT_TYPES:
        raise ValidationFailed(f"Unknown event_type '{et}'", details={"allowed": sorted(EVENT_TYPES)})
    if ev.get("source_status", "user_defined_simulation") not in SOURCE_STATUSES:
        raise ValidationFailed("Invalid source_status", details={"allowed": sorted(SOURCE_STATUSES)})
    start, end = ev.get("start_time_utc"), ev.get("end_time_utc")
    if start and end and end <= start:
        raise ValidationFailed("end_time_utc must be after start_time_utc")
    scope = ev.get("scope") or {}
    sev = float(ev.get("severity", 1.0))
    if not (0 <= sev <= 5):
        raise ValidationFailed("severity must be within [0, 5]")
    if et in {"edge_closure", "eta_increase"} or (et in {"traffic_surge", "stale_data"} and "edge_ids" in scope):
        ids = scope.get("edge_ids") or []
        if not ids:
            raise ValidationFailed(f"{et} requires scope.edge_ids")
        unknown = [e for e in ids if e not in rg.edge_ids]
        if unknown:
            raise ValidationFailed("Unknown edge ids in scope", details={"unknown": unknown[:10]})
    if et in {"restricted_polygon", "weather_penalty_zone"} or (et == "stale_data" and "polygon" in scope):
        poly = scope.get("polygon") or []
        if len(poly) < 3:
            raise ValidationFailed(f"{et} requires scope.polygon with >= 3 [lat, lon] vertices")
        for p in poly:
            if len(p) != 2 or not (-90 <= p[0] <= 90 and -180 <= p[1] <= 180):
                raise ValidationFailed("Polygon vertices must be valid [lat, lon] pairs")
    if et == "traffic_surge" and not (scope.get("edge_ids") or scope.get("cell_ids")):
        raise ValidationFailed("traffic_surge requires scope.edge_ids or scope.cell_ids")


def _normalize_dt(d: datetime | str) -> datetime:
    if isinstance(d, str):
        d = datetime.fromisoformat(d.replace("Z", "+00:00"))
    if d.tzinfo is not None:
        return d.astimezone(timezone.utc).replace(tzinfo=None)
    return d


def is_active(ev: dict[str, Any], t: datetime) -> bool:
    if not bool(ev.get("enabled", True)):
        return False
    t_norm = _normalize_dt(t)
    start_val = ev.get("start_time_utc")
    end_val = ev.get("end_time_utc")
    t_start = _normalize_dt(start_val) if start_val is not None else datetime.min
    t_end = _normalize_dt(end_val) if end_val is not None else datetime.max
    return t_start <= t_norm < t_end


def _edges_in_polygon(rg: RouteGraph, polygon: list[list[float]]) -> list[tuple[str, str]]:
    poly = Polygon([(lon, lat) for lat, lon in polygon])
    if not poly.is_valid:
        poly = poly.buffer(0)
    hits = []
    for u, v in rg.g.edges():
        line = LineString([(lo, la) for la, lo in rg.edge_geometry(u, v)])
        if line.intersects(poly):
            hits.append((u, v))
    return hits


def apply_events(ctx: RoutingContext, events: list[dict[str, Any]], rg: RouteGraph, grid: Grid) -> RoutingContext:
    """Return a NEW context with active events applied (input context is not mutated)."""
    out = ctx.copy()
    ids = rg.edge_ids
    edge_cells = {(u, v): set(grid.cells_along(*rg.pos(u), *rg.pos(v), step_km=40)) for u, v in rg.g.edges()}
    for ev in events:
        if not is_active(ev, ctx.scenario_time):
            continue
        et, scope, sev = ev["event_type"], ev.get("scope") or {}, float(ev.get("severity", 1.0))
        label = f"{ev['name']} [{ev.get('source_status', 'user_defined_simulation').upper()}]"
        if et in {"restricted_polygon", "weather_penalty_zone"} or (et == "stale_data" and "polygon" in scope):
            targets = _edges_in_polygon(rg, scope["polygon"])
        elif et == "traffic_surge" and scope.get("cell_ids"):
            cells = set(scope["cell_ids"])
            targets = [k for k, cs in edge_cells.items() if cs & cells]
        else:
            targets = [ids[e] for e in scope.get("edge_ids", []) if e in ids]
        for key in targets:
            a = out.edges[key]
            a.event_ids.append(ev["id"])
            if et in {"edge_closure", "restricted_polygon"}:
                a.closed = True
                a.closure_reasons.append(f"{'Closed segment' if et == 'edge_closure' else 'Restricted area'}: {label}")
            elif et == "traffic_surge":
                a.congestion_score = min(1.0, (a.congestion_score or 0.0) + sev)
                a.congestion_source = f"{a.congestion_source} + simulated surge"
                a.flags.append("simulated_traffic_surge")
            elif et == "weather_penalty_zone":
                a.weather_severity = min(1.0, (a.weather_severity or 0.0) + sev)
                a.weather_source = f"{a.weather_source} + simulated weather zone"
                a.flags.append("simulated_weather_zone")
            elif et == "eta_increase":
                a.time_min *= (1.0 + sev)
                a.time_source = f"{a.time_source} x{1 + sev:.2f} (simulated delay)"
                a.flags.append("simulated_eta_increase")
            elif et == "stale_data":
                a.uncertainty = min(1.0, a.uncertainty + sev)
                a.flags.append("stale_inputs_simulated")
        out.active_events.append({"id": ev["id"], "name": ev["name"], "event_type": et, "severity": sev,
                                  "source_status": ev.get("source_status"), "affected_edges": [ids_k for ids_k in
                                  (out.edges[k].edge_id for k in targets)]})
    if any(e["event_type"] == "stale_data" for e in out.active_events):
        out.warnings.append("Simulated stale-data event active: affected inputs carry raised uncertainty.")
    return out
