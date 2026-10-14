"""Intelligent CSV Schema Mapping and Field Recognition for Aviation, Weather, and Congestion Data."""
from __future__ import annotations

import re
from typing import Any
import numpy as np
import pandas as pd

from app.schemas.datasets import ColumnInfo

SCHEMA_DEFINITIONS: dict[str, dict[str, Any]] = {
    "aircraft_observations": {
        "required": [
            "source_aircraft_id",
            "timestamp_utc",
            "latitude",
            "longitude",
        ],
        "optional": [
            "altitude_m",
            "ground_speed_mps",
            "heading_deg",
            "vertical_rate_mps",
            "callsign",
            "on_ground",
            "last_contact_utc",
        ],
        "aliases": {
            "source_aircraft_id": ["icao24", "aircraft_id", "hex", "mode_s", "icao", "aircraft", "id", "transponder"],
            "timestamp_utc": ["time", "timestamp", "datetime", "date_time", "time_utc", "observed_at", "pos_time"],
            "latitude": ["lat", "latitude_deg", "pos_lat", "lat_deg", "y"],
            "longitude": ["lon", "lng", "longitude_deg", "pos_lon", "lon_deg", "x"],
            "altitude_m": ["altitude", "alt", "baro_altitude", "geo_altitude", "altitude_meter", "baro_alt_m"],
            "ground_speed_mps": ["velocity", "speed", "ground_speed", "gs", "spd", "speed_mps", "velocity_mps"],
            "heading_deg": ["heading", "track", "true_track", "course", "hdg", "bearing", "direction"],
            "vertical_rate_mps": ["vertical_rate", "climb_rate", "v_rate", "vertrate", "vertical_speed"],
            "callsign": ["call_sign", "flight", "flight_number", "ident", "operator_callsign"],
            "on_ground": ["ground", "surface", "is_ground", "onground", "ground_status"],
            "last_contact_utc": ["last_contact", "contact_time", "last_seen", "last_pos_update"],
        },
    },
    "weather_observations": {
        "required": [
            "latitude",
            "longitude",
            "valid_time_utc",
            "precipitation_mm",
        ],
        "optional": [
            "wind_speed_10m_ms",
            "wind_gusts_10m_ms",
            "cloud_cover_pct",
            "temperature_2m_c",
            "surface_pressure_hpa",
            "cell_id",
        ],
        "aliases": {
            "latitude": ["lat", "latitude_deg", "pos_lat", "lat_deg", "y"],
            "longitude": ["lon", "lng", "longitude_deg", "pos_lon", "lon_deg", "x"],
            "valid_time_utc": ["valid_time", "time", "timestamp", "datetime", "time_utc", "date_time", "observed_at"],
            "precipitation_mm": ["precip", "precipitation", "rain", "rainfall", "rain_mm", "precip_mm", "rate_mm", "precipitation_rate"],
            "wind_speed_10m_ms": ["wind_speed", "wind_spd", "wind_speed_mps", "wind_speed_ms", "speed", "wind"],
            "wind_gusts_10m_ms": ["wind_gusts", "gusts", "gust", "wind_gust", "gust_mps", "gust_ms"],
            "cloud_cover_pct": ["cloud_cover", "clouds", "cloud_pct", "cloud_cover_percentage", "tcdc"],
            "temperature_2m_c": ["temperature", "temp", "temp_c", "temperature_c", "t2m"],
            "surface_pressure_hpa": ["pressure", "surface_pressure", "pres", "pressure_hpa", "mslp", "sp"],
            "cell_id": ["cell", "grid_id", "cell_name", "sector", "sector_id"],
        },
    },
    "congestion_cells": {
        "required": [
            "cell_id",
            "aircraft_count",
            "congestion_score",
        ],
        "optional": [
            "predicted_class",
            "timestamp_utc",
        ],
        "aliases": {
            "cell_id": ["cell", "grid_id", "grid_cell", "sector_id", "sector", "id"],
            "aircraft_count": ["count", "flights", "traffic_count", "n_aircraft", "aircraft", "planes"],
            "congestion_score": ["score", "density_score", "congestion", "traffic_density", "density"],
            "predicted_class": ["class", "congestion_class", "level", "density_class", "state"],
            "timestamp_utc": ["time", "timestamp", "valid_time", "datetime", "time_window"],
        },
    },
}

REQUIRED_COLUMNS = SCHEMA_DEFINITIONS["aircraft_observations"]["required"]
OPTIONAL_COLUMNS = SCHEMA_DEFINITIONS["aircraft_observations"]["optional"]
CANDIDATE_ALIASES = SCHEMA_DEFINITIONS["aircraft_observations"]["aliases"]


def auto_detect_dataset_type(columns: list[str]) -> str:
    """Infers whether incoming CSV columns represent aircraft, weather, or congestion data."""
    clean_cols = [re.sub(r"[^a-z0-9_]", "", col.strip().lower()) for col in columns]

    # Weather indicators
    weather_keywords = {"precipitation", "precip", "rain", "rainfall", "cloudcover", "windgusts", "validtime"}
    if any(any(kw in c for kw in weather_keywords) for c in clean_cols):
        return "weather_observations"

    # Pre-aggregated congestion indicators
    congestion_keywords = {"congestion_score", "congestionscore", "aircraft_count", "aircraftcount", "cell_id"}
    if any(c in {"cell_id", "cell", "grid_id"} for c in clean_cols) and any(
        any(kw in c for kw in congestion_keywords) for c in clean_cols
    ):
        return "congestion_cells"

    return "aircraft_observations"


def auto_detect_mapping(columns: list[str], dataset_type: str = "aircraft_observations") -> dict[str, str]:
    """Auto-detects mapping from incoming column names to target canonical fields for specified dataset type."""
    schema = SCHEMA_DEFINITIONS.get(dataset_type, SCHEMA_DEFINITIONS["aircraft_observations"])
    req = schema["required"]
    opt = schema["optional"]
    aliases = schema["aliases"]

    normalized_cols = {col: re.sub(r"[^a-z0-9_]", "", col.strip().lower()) for col in columns}
    mapping: dict[str, str] = {}

    for target in req + opt:
        # 1. Exact match
        for orig_col, clean_col in normalized_cols.items():
            if clean_col == target:
                mapping[target] = orig_col
                break
        if target in mapping:
            continue

        # 2. Alias match
        cand = aliases.get(target, [])
        for orig_col, clean_col in normalized_cols.items():
            if clean_col in cand:
                mapping[target] = orig_col
                break

    return mapping


def analyze_dataframe_columns(df: pd.DataFrame, max_samples: int = 3) -> list[ColumnInfo]:
    """Generates column profiling details."""
    cols_info = []
    for col in df.columns:
        s = df[col]
        non_null = int(s.notna().sum())
        null_count = int(s.isna().sum())
        samples = [str(x) for x in s.dropna().head(max_samples).tolist()]
        cols_info.append(
            ColumnInfo(
                name=col,
                dtype=str(s.dtype),
                non_null_count=non_null,
                null_count=null_count,
                sample_values=samples,
            )
        )
    return cols_info


def validate_mapping(
    df_columns: list[str],
    mapping: dict[str, str],
    dataset_type: str = "aircraft_observations",
) -> tuple[bool, list[str]]:
    """Validates that all required columns are present in mapping and exist in the dataframe."""
    schema = SCHEMA_DEFINITIONS.get(dataset_type, SCHEMA_DEFINITIONS["aircraft_observations"])
    req = schema["required"]
    opt = schema["optional"]

    warnings: list[str] = []
    missing_required = []

    for r in req:
        mapped_col = mapping.get(r)
        if not mapped_col or mapped_col not in df_columns:
            missing_required.append(r)

    if missing_required:
        return False, [f"Missing required mapping for field(s) under '{dataset_type}': {', '.join(missing_required)}"]

    for o in opt:
        if o not in mapping or not mapping[o] or mapping[o] not in df_columns:
            warnings.append(f"Optional field '{o}' is unmapped. It will be initialized with null/NaN.")

    return True, warnings


def apply_mapping(
    df: pd.DataFrame,
    mapping: dict[str, str],
    dataset_type: str = "aircraft_observations",
) -> pd.DataFrame:
    """Renames mapped columns and adds missing standard columns with NaN for the dataset type."""
    schema = SCHEMA_DEFINITIONS.get(dataset_type, SCHEMA_DEFINITIONS["aircraft_observations"])
    req = schema["required"]
    opt = schema["optional"]

    rename_dict = {source_col: canonical for canonical, source_col in mapping.items() if source_col in df.columns}
    out = df.rename(columns=rename_dict).copy()

    for col in req + opt:
        if col not in out.columns:
            out[col] = np.nan

    return out
