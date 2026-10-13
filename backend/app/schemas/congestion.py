"""Congestion and model inference schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class CongestionCellItem(BaseModel):
    cell_id: str
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float
    center_lat: float
    center_lon: float
    is_corridor: bool
    predicted_class: str | None = None
    predicted_score: float | None = None
    probabilities: dict[str, float] | None = None
    confidence: float | None = None
    out_of_distribution: list[str] = Field(default_factory=list)


class CongestionLayerResponse(BaseModel):
    window_time_utc: datetime
    cells: list[CongestionCellItem]
    source_label: str
    warnings: list[str] = Field(default_factory=list)


class CellTimeseriesPoint(BaseModel):
    window_start_utc: datetime
    aircraft_count: int
    observation_count: int
    mean_speed_mps: float | None = None
    observed_class: str | None = None


class CellTimeseriesResponse(BaseModel):
    cell_id: str
    points: list[CellTimeseriesPoint]
    total_points: int


class ModelStatusItem(BaseModel):
    kind: str
    active_version: str | None
    model_name: str | None = None
    task: str | None = None
    trained_at_utc: str | None = None
    data_kind: str = "synthetic"
    is_available: bool = False
    metrics: dict[str, Any] = Field(default_factory=dict)
