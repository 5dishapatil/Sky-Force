"""SQLAlchemy 2.x ORM models.

Every table that holds data carries provenance (``source`` / ``dataset`` /
``is_synthetic``) so that synthetic demonstration content can never be
confused with observed data.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Airport(Base):
    __tablename__ = "airports"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    icao: Mapped[str | None] = mapped_column(String(8), index=True)
    iata: Mapped[str | None] = mapped_column(String(8), index=True)
    name: Mapped[str] = mapped_column(String(200))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    country: Mapped[str | None] = mapped_column(String(8))
    elevation_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    source: Mapped[str] = mapped_column(String(64))
    provenance: Mapped[str] = mapped_column(Text)


class Waypoint(Base):
    __tablename__ = "waypoints"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    node_id: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(100))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    kind: Mapped[str] = mapped_column(String(32), default="research_synthetic")
    source: Mapped[str] = mapped_column(String(64))
    provenance: Mapped[str] = mapped_column(Text)


class RouteEdge(Base):
    __tablename__ = "route_edges"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    edge_id: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    source_node: Mapped[str] = mapped_column(String(16), index=True)
    target_node: Mapped[str] = mapped_column(String(16), index=True)
    distance_km: Mapped[float] = mapped_column(Float)
    bearing_deg: Mapped[float] = mapped_column(Float)
    is_synthetic: Mapped[bool] = mapped_column(Boolean, default=True)
    provenance: Mapped[str] = mapped_column(Text)


class InferredTrack(Base):
    __tablename__ = "inferred_tracks"
    track_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset: Mapped[str] = mapped_column(String(64), index=True)
    source_aircraft_id: Mapped[str] = mapped_column(String(16), index=True)
    callsign: Mapped[str | None] = mapped_column(String(16), nullable=True)
    start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    n_observations: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(128))
    is_inferred: Mapped[bool] = mapped_column(Boolean, default=True)


class AircraftObservation(Base):
    __tablename__ = "aircraft_observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    observation_id: Mapped[str] = mapped_column(String(64), index=True)
    dataset: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(64))
    is_synthetic: Mapped[bool] = mapped_column(Boolean)
    source_aircraft_id: Mapped[str] = mapped_column(String(16), index=True)
    callsign: Mapped[str | None] = mapped_column(String(16), nullable=True)
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    altitude_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    ground_speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    vertical_rate_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    on_ground: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    last_contact_utc: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    data_quality_flags: Mapped[str] = mapped_column(String(200), default="")
    track_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_obs_dataset_time", "dataset", "timestamp_utc"),)


class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset: Mapped[str] = mapped_column(String(64), index=True)
    source: Mapped[str] = mapped_column(String(64))
    product: Mapped[str] = mapped_column(String(128))
    is_synthetic: Mapped[bool] = mapped_column(Boolean)
    location_type: Mapped[str] = mapped_column(String(16))  # grid_cell | airport
    location_id: Mapped[str] = mapped_column(String(32), index=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    valid_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    temperature_2m_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    relative_humidity_2m_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    surface_pressure_hpa: Mapped[float | None] = mapped_column(Float, nullable=True)
    precipitation_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    cloud_cover_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_10m_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_direction_10m_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_gusts_10m_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    wind_speed_100m_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index("ix_wx_dataset_loc_time", "dataset", "location_id", "valid_time_utc"),)


class SpatialCell(Base):
    __tablename__ = "spatial_cells"
    cell_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    lat_min: Mapped[float] = mapped_column(Float)
    lat_max: Mapped[float] = mapped_column(Float)
    lon_min: Mapped[float] = mapped_column(Float)
    lon_max: Mapped[float] = mapped_column(Float)
    grid_deg: Mapped[float] = mapped_column(Float)
    is_corridor: Mapped[bool] = mapped_column(Boolean, default=False)


class CongestionObservation(Base):
    """Per-cell / per-window traffic aggregate (research aggregation unit, not an ATC sector)."""

    __tablename__ = "congestion_observations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    dataset: Mapped[str] = mapped_column(String(64), index=True)
    cell_id: Mapped[str] = mapped_column(String(16), index=True)
    window_start_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    window_end_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    aircraft_count: Mapped[int] = mapped_column(Integer)
    observation_count: Mapped[int] = mapped_column(Integer)
    mean_speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_std_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    mean_altitude_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_class: Mapped[str | None] = mapped_column(String(8), nullable=True)

    __table_args__ = (
        UniqueConstraint("dataset", "cell_id", "window_start_utc", name="uq_cong_cell_window"),
    )


class Scenario(Base):
    __tablename__ = "scenarios"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    is_prebuilt: Mapped[bool] = mapped_column(Boolean, default=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)
    seed: Mapped[int] = mapped_column(Integer, default=0)
    scenario_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    events: Mapped[list["ScenarioEvent"]] = relationship(
        back_populates="scenario", cascade="all, delete-orphan", order_by="ScenarioEvent.start_time_utc"
    )


class ScenarioEvent(Base):
    __tablename__ = "scenario_events"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(ForeignKey("scenarios.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text, default="")
    event_type: Mapped[str] = mapped_column(String(32))
    start_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    end_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    scope: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    severity: Mapped[float] = mapped_column(Float, default=1.0)
    source_status: Mapped[str] = mapped_column(String(32), default="user_defined_simulation")
    original: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    scenario: Mapped[Scenario] = relationship(back_populates="events")


class ModelArtifactMetadata(Base):
    __tablename__ = "model_artifacts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    model_kind: Mapped[str] = mapped_column(String(32), index=True)  # congestion | eta
    version: Mapped[str] = mapped_column(String(64))
    path: Mapped[str] = mapped_column(Text)
    trained_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    data_kind: Mapped[str] = mapped_column(String(16))  # synthetic | real
    dataset_id: Mapped[str] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ExperimentRun(Base):
    __tablename__ = "experiment_runs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(16))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    config: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    artifact_dir: Mapped[str | None] = mapped_column(Text, nullable=True)
    route_evaluations: Mapped[list["RouteEvaluation"]] = relationship(
        back_populates="experiment", cascade="all, delete-orphan"
    )


class RouteEvaluation(Base):
    __tablename__ = "route_evaluations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    experiment_id: Mapped[str | None] = mapped_column(ForeignKey("experiment_runs.id", ondelete="CASCADE"), index=True)
    scenario_id: Mapped[str] = mapped_column(String(64))
    origin: Mapped[str] = mapped_column(String(16))
    destination: Mapped[str] = mapped_column(String(16))
    algorithm: Mapped[str] = mapped_column(String(16))
    objective: Mapped[str] = mapped_column(String(16))
    route_found: Mapped[bool] = mapped_column(Boolean)
    route_distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    estimated_time_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    weather_penalty: Mapped[float | None] = mapped_column(Float, nullable=True)
    congestion_penalty: Mapped[float | None] = mapped_column(Float, nullable=True)
    total_composite_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    replanning_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    closed_edges_in_route: Mapped[int | None] = mapped_column(Integer, nullable=True)
    nodes_expanded: Mapped[int | None] = mapped_column(Integer, nullable=True)
    path: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    experiment: Mapped[ExperimentRun | None] = relationship(back_populates="route_evaluations")


class DataSourceSnapshot(Base):
    __tablename__ = "data_source_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_key: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(24))  # connected | local_file | cached | synthetic | unavailable | error
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    record_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    details: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)


class ConflictAnalysisRun(Base):
    __tablename__ = "conflict_analysis_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    dataset: Mapped[str] = mapped_column(String(64))
    snapshot_time_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    thresholds: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    events: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
