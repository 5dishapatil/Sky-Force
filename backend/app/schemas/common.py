"""Shared and system API response models."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    app_name: str
    environment: str
    database: str
    timestamp_utc: datetime
    disclaimer: str


class MetaResponse(BaseModel):
    app_name: str
    version: str
    disclaimer: str
    research_questions: list[str]
    active_dataset: str
    active_models: dict[str, str | None]
    coverage_utc: list[datetime | None]


class DataSourceStatusItem(BaseModel):
    source_key: str
    status: str
    retrieved_at_utc: datetime | None = None
    record_count: int | None = None
    message: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class DataQualitySummaryResponse(BaseModel):
    dataset: str
    input_rows: int
    retained_rows: int
    dropped: dict[str, int]
    flagged: dict[str, int]
    missing_profile_pct: dict[str, float]
    time_range_utc: list[str | None]
    inferred_tracks: int
    generated_at_utc: str
