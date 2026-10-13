"""Airports, waypoints, and candidate route network endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models as m
from app.db.session import get_db
from app.schemas.airports import AirportItem, AirspaceNetworkResponse, RouteEdgeItem, WaypointItem

router = APIRouter(prefix="/airports", tags=["Airports & Network"])


@router.get("", response_model=list[AirportItem])
def list_airports(db: Session = Depends(get_db)) -> list[AirportItem]:
    airports = db.scalars(select(m.Airport).order_by(m.Airport.node_id)).all()
    return [
        AirportItem(
            node_id=a.node_id,
            icao=a.icao,
            iata=a.iata,
            name=a.name,
            latitude=a.latitude,
            longitude=a.longitude,
            country=a.country,
            elevation_m=a.elevation_m,
            source=a.source,
            provenance=a.provenance,
        )
        for a in airports
    ]


@router.get("/network", response_model=AirspaceNetworkResponse)
def get_airspace_network(db: Session = Depends(get_db)) -> AirspaceNetworkResponse:
    airports = db.scalars(select(m.Airport)).all()
    waypoints = db.scalars(select(m.Waypoint)).all()
    edges = db.scalars(select(m.RouteEdge)).all()

    ap_items = [
        AirportItem(
            node_id=a.node_id,
            icao=a.icao,
            iata=a.iata,
            name=a.name,
            latitude=a.latitude,
            longitude=a.longitude,
            country=a.country,
            elevation_m=a.elevation_m,
            source=a.source,
            provenance=a.provenance,
        )
        for a in airports
    ]
    wp_items = [
        WaypointItem(
            node_id=w.node_id,
            name=w.name,
            latitude=w.latitude,
            longitude=w.longitude,
            kind=w.kind,
            source=w.source,
        )
        for w in waypoints
    ]
    edge_items = [
        RouteEdgeItem(
            edge_id=e.edge_id,
            source_node=e.source_node,
            target_node=e.target_node,
            distance_km=e.distance_km,
            bearing_deg=e.bearing_deg,
            is_synthetic=e.is_synthetic,
        )
        for e in edges
    ]

    return AirspaceNetworkResponse(
        airports=ap_items,
        waypoints=wp_items,
        edges=edge_items,
        total_airports=len(ap_items),
        total_waypoints=len(wp_items),
        total_edges=len(edge_items),
    )
