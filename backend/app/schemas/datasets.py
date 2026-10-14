"""Dataset Studio and pipeline API schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class SchemaMappingConfig(BaseModel):
    """Aircraft observations schema mapping config."""
    source_aircraft_id: str = "source_aircraft_id"
    timestamp_utc: str = "timestamp_utc"
    latitude: str = "latitude"
    longitude: str = "longitude"
    altitude_m: str | None = "altitude_m"
    ground_speed_mps: str | None = "ground_speed_mps"
    heading_deg: str | None = "heading_deg"
    vertical_rate_mps: str | None = "vertical_rate_mps"
    callsign: str | None = "callsign"
    on_ground: str | None = "on_ground"
    last_contact_utc: str | None = "last_contact_utc"


class WeatherSchemaMappingConfig(BaseModel):
    """Weather observations and grid schema mapping config."""
    latitude: str = "latitude"
    longitude: str = "longitude"
    valid_time_utc: str = "valid_time_utc"
    precipitation_mm: str = "precipitation_mm"
    wind_speed_10m_ms: str | None = "wind_speed_10m_ms"
    wind_gusts_10m_ms: str | None = "wind_gusts_10m_ms"
    cloud_cover_pct: str | None = "cloud_cover_pct"
    temperature_2m_c: str | None = "temperature_2m_c"
    surface_pressure_hpa: str | None = "surface_pressure_hpa"
    cell_id: str | None = "cell_id"


class CongestionSchemaMappingConfig(BaseModel):
    """Pre-aggregated congestion cells schema mapping config."""
    cell_id: str = "cell_id"
    aircraft_count: str = "aircraft_count"
    congestion_score: str = "congestion_score"
    predicted_class: str | None = "predicted_class"
    timestamp_utc: str | None = "timestamp_utc"


class ColumnInfo(BaseModel):
    name: str
    dtype: str
    non_null_count: int
    null_count: int
    sample_values: list[Any] = Field(default_factory=list)


class DatasetUploadResponse(BaseModel):
    dataset_id: str
    filename: str
    dataset_type: str = "aircraft_observations"
    file_size_bytes: int
    row_count: int
    col_count: int
    detected_columns: list[str]
    suggested_mapping: dict[str, str]
    columns_info: list[ColumnInfo]
    is_valid_format: bool
    validation_warnings: list[str] = Field(default_factory=list)
    upload_timestamp_utc: datetime


class DatasetSummaryItem(BaseModel):
    id: str
    filename: str
    dataset_type: str = "aircraft_observations"
    file_size_bytes: int
    row_count: int
    col_count: int
    uploaded_at_utc: datetime
    status: str
    is_active: bool = False
    pipeline_stages: dict[str, str] = Field(default_factory=dict)
    provenance: str = "user_upload"
    linked_weather_dataset_id: str | None = None


class DatasetDetailResponse(BaseModel):
    id: str
    filename: str
    dataset_type: str = "aircraft_observations"
    file_size_bytes: int
    row_count: int
    col_count: int
    uploaded_at_utc: datetime
    status: str
    schema_mapping: dict[str, str] = Field(default_factory=dict)
    validation_report: dict[str, Any] = Field(default_factory=dict)
    pipeline_runs: list[dict[str, Any]] = Field(default_factory=list)
    available_artifacts: dict[str, str] = Field(default_factory=dict)
    active_in_routing: bool = False
    provenance: str = "user_upload"
    linked_weather_dataset_id: str | None = None


class DatasetRawPreviewResponse(BaseModel):
    dataset_id: str
    filename: str
    total_rows: int
    page: int
    page_size: int
    columns: list[str]
    rows: list[dict[str, Any]]


class RunPipelineRequest(BaseModel):
    stages: list[str] = Field(
        default_factory=lambda: ["quality", "segmentation", "features", "inference"],
        description="Stages to execute: quality, segmentation, features, inference, weather_indexing",
    )
    custom_mapping: dict[str, str] | None = None


class PipelineStageResult(BaseModel):
    stage: str
    status: str
    elapsed_seconds: float
    output_summary: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class RunPipelineResponse(BaseModel):
    dataset_id: str
    status: str
    total_elapsed_seconds: float
    stages: list[PipelineStageResult]
    artifact_paths: dict[str, str] = Field(default_factory=dict)


class LinkWeatherRequest(BaseModel):
    weather_dataset_id: str
    spatial_tolerance_deg: float = 0.5
    temporal_tolerance_seconds: int = 3600


class LinkWeatherResponse(BaseModel):
    aircraft_dataset_id: str
    weather_dataset_id: str
    status: str
    total_traffic_rows: int
    matched_rows: int
    unmatched_rows: int
    coverage_percentage: float
    warnings: list[str] = Field(default_factory=list)
    artifact_path: str
