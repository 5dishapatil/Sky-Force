"""Conflict risk and proximity analysis schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ConflictScanRequest(BaseModel):
    timestamp_utc: datetime | None = None
    forecast_horizon_seconds: float = 300.0
    horizontal_threshold_km: float = 9.26  # ~5 NM
    vertical_threshold_m: float = 300.0    # ~1000 ft


class ConflictEventItem(BaseModel):
    event_id: str
    aircraft_1: str
    callsign_1: str | None = None
    aircraft_2: str
    callsign_2: str | None = None
    observation_time_utc: datetime
    current_horizontal_dist_km: float
    current_vertical_diff_m: float | None = None
    cpa_time_seconds: float
    cpa_horizontal_dist_km: float
    cpa_vertical_diff_m: float | None = None
    severity: str
    is_projected: bool
    data_uncertainty_flags: list[str] = Field(default_factory=list)
    disclaimer: str = "Research prototype proximity estimate only. Not an operational separation standard."


class ConflictScanResponse(BaseModel):
    timestamp_utc: datetime
    aircraft_scanned: int
    pairs_evaluated: int
    proximity_events_found: int
    events: list[ConflictEventItem]
    parameters: dict[str, Any]
    disclaimer: str
