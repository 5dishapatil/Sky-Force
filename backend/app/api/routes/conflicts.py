"""Airspace conflict risk and proximity analysis endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import models as m
from app.db.session import get_db
from app.schemas.conflicts import ConflictEventItem, ConflictScanRequest, ConflictScanResponse
from app.services.conflict_analysis.cpa import AircraftState, scan_airspace_conflicts

router = APIRouter(prefix="/conflicts", tags=["Conflict & Proximity Analysis"])


def _load_aircraft_states_at_time(
    db: Session,
    timestamp_utc: datetime | None,
    tolerance_seconds: int = 180,
) -> tuple[datetime, list[AircraftState]]:
    """Loads active aircraft observations around a given or latest timestamp."""
    if timestamp_utc is None:
        # Find latest observation timestamp in DB
        latest_ts = db.scalar(select(func.max(m.AircraftObservation.timestamp_utc)))
        if latest_ts is None:
            return datetime.now(timezone.utc), []
        target_ts = latest_ts
    else:
        target_ts = timestamp_utc.replace(tzinfo=None)

    # Find observations within tolerance_seconds
    rows = db.scalars(
        select(m.AircraftObservation)
        .where(
            m.AircraftObservation.timestamp_utc >= target_ts,
        )
        .order_by(m.AircraftObservation.timestamp_utc.asc())
        .limit(200)
    ).all()

    # Group by aircraft_id to keep latest observation per aircraft
    by_ac: dict[str, m.AircraftObservation] = {}
    for r in rows:
        if r.source_aircraft_id not in by_ac:
            by_ac[r.source_aircraft_id] = r

    states: list[AircraftState] = []
    for ac_id, r in by_ac.items():
        if r.latitude is None or r.longitude is None:
            continue
        uncertainty: list[str] = []
        if r.altitude_m is None:
            uncertainty.append("MISSING_ALTITUDE")
        if r.ground_speed_mps is None or r.heading_deg is None:
            uncertainty.append("INCOMPLETE_VELOCITY")

        states.append(
            AircraftState(
                aircraft_id=ac_id,
                callsign=r.callsign,
                timestamp_utc=r.timestamp_utc.replace(tzinfo=timezone.utc),
                latitude=r.latitude,
                longitude=r.longitude,
                altitude_m=r.altitude_m,
                ground_speed_mps=r.ground_speed_mps,
                heading_deg=r.heading_deg,
                vertical_rate_mps=r.vertical_rate_mps,
                is_synthetic=bool(r.is_synthetic),
                uncertainty_flags=uncertainty,
            )
        )

    return target_ts.replace(tzinfo=timezone.utc), states


@router.post("/analyze", response_model=ConflictScanResponse)
def analyze_conflicts(
    req: ConflictScanRequest,
    db: Session = Depends(get_db),
) -> ConflictScanResponse:
    scan_time, states = _load_aircraft_states_at_time(
        db=db,
        timestamp_utc=req.timestamp_utc,
    )

    events = scan_airspace_conflicts(
        states=states,
        horizon_s=req.forecast_horizon_seconds,
        horiz_thresh_km=req.horizontal_threshold_km,
        vert_thresh_m=req.vertical_threshold_m,
    )

    n_pairs = (len(states) * (len(states) - 1)) // 2 if len(states) > 1 else 0

    event_items = [
        ConflictEventItem(
            event_id=e.event_id,
            aircraft_1=e.aircraft_1,
            callsign_1=e.callsign_1,
            aircraft_2=e.aircraft_2,
            callsign_2=e.callsign_2,
            observation_time_utc=e.observation_time_utc,
            current_horizontal_dist_km=round(e.current_horizontal_dist_km, 2),
            current_vertical_diff_m=round(e.current_vertical_diff_m, 1) if e.current_vertical_diff_m is not None else None,
            cpa_time_seconds=round(e.cpa_time_seconds, 1),
            cpa_horizontal_dist_km=round(e.cpa_horizontal_dist_km, 2),
            cpa_vertical_diff_m=round(e.cpa_vertical_diff_m, 1) if e.cpa_vertical_diff_m is not None else None,
            severity=e.severity,
            is_projected=e.is_projected,
            data_uncertainty_flags=e.data_uncertainty_flags,
            disclaimer="Research prototype proximity estimate only. Not an operational separation standard.",
        )
        for e in events
    ]

    return ConflictScanResponse(
        timestamp_utc=scan_time,
        aircraft_scanned=len(states),
        pairs_evaluated=n_pairs,
        proximity_events_found=len(event_items),
        events=event_items,
        parameters={
            "forecast_horizon_seconds": req.forecast_horizon_seconds,
            "horizontal_threshold_km": req.horizontal_threshold_km,
            "vertical_threshold_m": req.vertical_threshold_m,
        },
        disclaimer="Research prototype for simulation and decision support. Not approved for operational flight planning, navigation, or air traffic control.",
    )


@router.get("/latest", response_model=ConflictScanResponse)
def get_latest_conflicts(
    horizon_seconds: float = Query(300.0, description="Forecast horizon in seconds"),
    horiz_threshold_km: float = Query(9.26, description="Horizontal proximity threshold km (~5 NM)"),
    vert_threshold_m: float = Query(300.0, description="Vertical proximity threshold meters (~1000 ft)"),
    db: Session = Depends(get_db),
) -> ConflictScanResponse:
    req = ConflictScanRequest(
        timestamp_utc=None,
        forecast_horizon_seconds=horizon_seconds,
        horizontal_threshold_km=horiz_threshold_km,
        vertical_threshold_m=vert_threshold_m,
    )
    return analyze_conflicts(req=req, db=db)
