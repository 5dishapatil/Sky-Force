"""Airports and airspace network schemas."""
from __future__ import annotations

from pydantic import BaseModel


class AirportItem(BaseModel):
    node_id: str
    icao: str | None = None
    iata: str | None = None
    name: str
    latitude: float
    longitude: float
    country: str | None = None
    elevation_m: float | None = None
    source: str = "OurAirports"
    provenance: str = ""


class WaypointItem(BaseModel):
    node_id: str
    name: str
    latitude: float
    longitude: float
    kind: str
    source: str = "synthetic_demo"


class RouteEdgeItem(BaseModel):
    edge_id: str
    source_node: str
    target_node: str
    distance_km: float
    bearing_deg: float
    is_synthetic: bool = True


class AirspaceNetworkResponse(BaseModel):
    airports: list[AirportItem]
    waypoints: list[WaypointItem]
    edges: list[RouteEdgeItem]
    total_airports: int
    total_waypoints: int
    total_edges: int
