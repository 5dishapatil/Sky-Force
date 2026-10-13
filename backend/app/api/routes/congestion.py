"""Congestion prediction and grid layers endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.state import get_state
from app.db import models as m
from app.db.session import get_db
from app.schemas.congestion import (
    CellTimeseriesPoint,
    CellTimeseriesResponse,
    CongestionCellItem,
    CongestionLayerResponse,
)

router = APIRouter(prefix="/congestion", tags=["Congestion & Prediction"])


@router.get("/cells", response_model=CongestionLayerResponse)
def get_congestion_cells(
    time_utc: datetime | None = Query(None, description="Scenario timestamp in UTC"),
    db: Session = Depends(get_db),
) -> CongestionLayerResponse:
    state = get_state()
    t = time_utc or state.settings.default_scenario_time_utc
    if t.tzinfo is None:
        t = t.replace(tzinfo=timezone.utc)

    # 1. Fetch grid cells
    db_cells = db.scalars(select(m.SpatialCell)).all()
    
    # 2. Predict cells via ContextBuilder
    pred_dict, src_label, warnings = state.context_builder.cell_predictions(t)

    items: list[CongestionCellItem] = []
    for c in db_cells:
        pred = pred_dict.get(c.cell_id, {})
        items.append(
            CongestionCellItem(
                cell_id=c.cell_id,
                lat_min=c.lat_min,
                lat_max=c.lat_max,
                lon_min=c.lon_min,
                lon_max=c.lon_max,
                center_lat=(c.lat_min + c.lat_max) / 2.0,
                center_lon=(c.lon_min + c.lon_max) / 2.0,
                is_corridor=c.is_corridor,
                predicted_class=pred.get("class"),
                predicted_score=pred.get("score"),
                probabilities=pred.get("probs"),
                confidence=pred.get("confidence"),
                out_of_distribution=pred.get("ood", []),
            )
        )

    return CongestionLayerResponse(
        window_time_utc=t,
        cells=items,
        source_label=src_label,
        warnings=warnings,
    )


@router.get("/timeseries", response_model=CellTimeseriesResponse)
def get_cell_timeseries(
    cell_id: str = Query(..., description="Cell identifier e.g. R08C03"),
    limit: int = Query(96, le=500),
    db: Session = Depends(get_db),
) -> CellTimeseriesResponse:
    rows = db.scalars(
        select(m.CongestionObservation)
        .where(m.CongestionObservation.cell_id == cell_id)
        .order_by(m.CongestionObservation.window_start_utc.asc())
        .limit(limit)
    ).all()

    points = [
        CellTimeseriesPoint(
            window_start_utc=r.window_start_utc,
            aircraft_count=r.aircraft_count,
            observation_count=r.observation_count,
            mean_speed_mps=r.mean_speed_mps,
            observed_class=r.observed_class,
        )
        for r in rows
    ]

    return CellTimeseriesResponse(
        cell_id=cell_id,
        points=points,
        total_points=len(points),
    )
