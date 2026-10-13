"""Demo bootstrap pipeline.

generate synthetic world -> write raw files -> data-quality -> track inference
-> aggregation / ETA traversals -> persist to DB -> manifest -> seed scenarios.

Re-running is idempotent: rows belonging to the demo dataset are replaced.
"""
from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.logging import get_logger, log_event
from app.db import models as m
from app.db.migrate import upgrade_to_head
from app.db.session import session_scope
from app.services.features.congestion import aggregate_windows, classify, thresholds_from_training
from app.services.features.eta import extract_traversals
from app.services.features.splits import demo_boundaries
from app.services.geospatial.grid import grid_from_settings
from app.services.ingestion.manifest import file_sha256, upsert_entry
from app.services.ingestion.ourairports import load_subset
from app.services.ingestion.synthetic_demo import generate_world
from app.services.preprocessing.quality import run_quality, segment_tracks

logger = get_logger(__name__)


def airports_frame() -> tuple[pd.DataFrame, dict]:
    df, meta = load_subset()
    out = pd.DataFrame({
        "node_id": df["ident"], "icao": df["gps_code"].fillna(df["ident"]), "iata": df["iata_code"],
        "name": df["name"], "latitude": df["latitude_deg"].astype(float), "longitude": df["longitude_deg"].astype(float),
        "country": df["iso_country"], "elevation_m": (df["elevation_ft"].astype(float) * 0.3048).round(1),
    })
    out["source"] = "ourairports"
    out["provenance"] = (
        f"OurAirports airports.csv (public domain), retrieved {meta.get('retrieved_at_utc', 'unknown')}, "
        f"sha256 {str(meta.get('full_file_sha256', ''))[:12]}..."
    )
    return out, meta


def _naive(series: pd.Series) -> list:
    """tz-aware pandas -> naive-UTC python datetimes (portable across SQLite/PostgreSQL)."""
    s = pd.to_datetime(series, utc=True).dt.tz_convert("UTC").dt.tz_localize(None)
    return [None if pd.isna(v) else v.to_pydatetime() for v in s]


def _records(df: pd.DataFrame) -> list[dict]:
    df = df.astype(object).where(pd.notna(df), None)
    return df.to_dict("records")


def _bulk(session: Session, model, df: pd.DataFrame, chunk: int = 20000) -> None:  # noqa: ANN001
    recs = _records(df)
    for i in range(0, len(recs), chunk):
        session.execute(insert(model), recs[i:i + chunk])


def run_bootstrap(settings: Settings) -> dict:
    t0 = time.perf_counter()
    dirs = {k: settings.data_dir / k for k in ("raw", "interim", "processed", "synthetic")}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    grid = grid_from_settings(settings)
    bounds = demo_boundaries(settings)
    ds = settings.demo_dataset_id

    airports, ap_meta = airports_frame()
    world = generate_world(airports, grid, settings.demo_start_utc, settings.demo_days, settings.demo_flights_per_day,
                           settings.demo_sample_seconds, settings.window_minutes, settings.demo_seed)
    log_event(logger, "synthetic world generated", observations=len(world.observations), secs=round(time.perf_counter() - t0, 1))

    # ---- raw synthetic files -------------------------------------------------
    raw_obs_path = dirs["synthetic"] / "observations_raw.parquet"
    world.observations.drop(columns=["flight_index"]).to_parquet(raw_obs_path, index=False)
    world.weather.to_parquet(dirs["synthetic"] / "weather_synthetic.parquet", index=False)
    world.flights.to_parquet(dirs["synthetic"] / "flights_ground_truth.parquet", index=False)
    world.fault_log.to_csv(dirs["synthetic"] / "injected_faults.csv", index=False)
    world.waypoints.to_csv(dirs["synthetic"] / "waypoints.csv", index=False)
    world.edges.to_csv(dirs["synthetic"] / "edges.csv", index=False)

    # ---- data quality + tracks ----------------------------------------------
    raw = pd.read_parquet(raw_obs_path)
    clean, report = run_quality(raw)
    clean, tracks = segment_tracks(clean)
    clean.to_parquet(dirs["processed"] / "observations_clean.parquet", index=False)
    rep = report.to_dict()
    rep["dataset"] = ds
    rep["inferred_tracks"] = int(len(tracks))
    rep["injected_fault_ground_truth"] = world.meta.get("injected_faults", {})
    (dirs["processed"] / "data_quality_report.json").write_text(json.dumps(rep, indent=2))

    # ---- aggregation, thresholds, traversals ---------------------------------
    nodes = pd.concat([airports[["node_id", "latitude", "longitude"]], world.waypoints[["node_id", "latitude", "longitude"]]], ignore_index=True)
    pos = {r.node_id: (r.latitude, r.longitude) for r in nodes.itertuples()}
    corridor = sorted({c for e in world.edges.itertuples() for c in grid.cells_along(*pos[e.source_node], *pos[e.target_node])})
    agg = aggregate_windows(clean, grid, settings.window_minutes)
    agg = agg[agg.cell_id.isin(corridor)].reset_index(drop=True)
    # thresholds from TRAINING partition only (zero-filled counts of corridor cells)
    train_windows = pd.date_range(bounds.start, bounds.val_start, freq=f"{settings.window_minutes}min", inclusive="left")
    full_train = pd.MultiIndex.from_product([corridor, train_windows], names=["cell_id", "window_start_utc"]).to_frame(index=False)
    full_train = full_train.merge(agg[["cell_id", "window_start_utc", "aircraft_count"]], how="left").fillna({"aircraft_count": 0})
    th = thresholds_from_training(full_train.aircraft_count)
    (dirs["processed"] / "congestion_thresholds.json").write_text(json.dumps({**th.to_dict(), "fitted_on": "train", "splits": bounds.to_dict()}, indent=2))
    agg["observed_class"] = classify(agg.aircraft_count, th)
    agg.to_parquet(dirs["processed"] / "congestion_agg.parquet", index=False)

    trav, trav_stats = extract_traversals(clean, nodes, world.edges, sample_s=settings.demo_sample_seconds)
    trav.to_parquet(dirs["processed"] / "eta_traversals.parquet", index=False)
    (dirs["processed"] / "eta_traversal_stats.json").write_text(json.dumps(trav_stats, indent=2))

    # ---- database ------------------------------------------------------------
    upgrade_to_head(settings.database_url)
    with session_scope(settings.database_url) as s:
        for model in (m.AircraftObservation, m.InferredTrack, m.WeatherObservation, m.CongestionObservation):
            s.execute(delete(model).where(model.dataset == ds))
        for model in (m.Airport, m.Waypoint, m.RouteEdge, m.SpatialCell):
            s.execute(delete(model))
        _bulk(s, m.Airport, airports)
        _bulk(s, m.Waypoint, world.waypoints)
        _bulk(s, m.RouteEdge, world.edges)
        cells = []
        for r in range(grid.n_rows):
            for c in range(grid.n_cols):
                cid = grid.cell_id_from_rc(r, c)
                a, b, lo0, lo1 = grid.bounds(cid)
                cells.append({"cell_id": cid, "lat_min": a, "lat_max": b, "lon_min": lo0, "lon_max": lo1,
                              "grid_deg": grid.deg, "is_corridor": cid in corridor})
        s.execute(insert(m.SpatialCell), cells)

        obs = clean[["observation_id", "source", "is_synthetic", "source_aircraft_id", "callsign", "latitude", "longitude",
                     "altitude_m", "ground_speed_mps", "heading_deg", "vertical_rate_mps", "on_ground", "data_quality_flags", "track_id"]].copy()
        obs["dataset"] = ds
        obs["timestamp_utc"] = _naive(clean["timestamp_utc"])
        obs["last_contact_utc"] = _naive(clean["last_contact_utc"])
        obs["retrieved_at"] = datetime.now(timezone.utc).replace(tzinfo=None)
        _bulk(s, m.AircraftObservation, obs)

        tr = tracks.copy()
        tr["dataset"] = ds
        tr["start_utc"] = _naive(tracks.start_utc)
        tr["end_utc"] = _naive(tracks.end_utc)
        tr["is_inferred"] = True
        _bulk(s, m.InferredTrack, tr)

        wx = world.weather.copy()
        wx["valid_time_utc"] = _naive(wx.valid_time_utc)
        wx["dataset"] = ds
        wx["source"] = "synthetic_demo"
        wx["product"] = "Synthetic hourly field on research grid (documented generator assumptions)"
        wx["is_synthetic"] = True
        wx["location_type"] = "grid_cell"
        _bulk(s, m.WeatherObservation, wx)

        ag = agg.copy()
        ag["dataset"] = ds
        ag["window_start_utc"] = _naive(agg.window_start_utc)
        ag["window_end_utc"] = _naive(agg.window_end_utc)
        ag = ag.drop(columns=[c for c in ag.columns if c not in {
            "dataset", "cell_id", "window_start_utc", "window_end_utc", "aircraft_count", "observation_count",
            "mean_speed_mps", "speed_std_mps", "mean_altitude_m", "observed_class"}])
        _bulk(s, m.CongestionObservation, ag)

        now = datetime.now(timezone.utc)
        s.add(m.DataSourceSnapshot(source_key="synthetic_demo", status="synthetic", retrieved_at=now,
                                   record_count=int(len(clean)),
                                   message="Deterministic synthetic demonstration dataset generated locally.",
                                   details={"dataset": ds, "seed": settings.demo_seed}))
        s.add(m.DataSourceSnapshot(source_key="ourairports", status="local_file", retrieved_at=now,
                                   record_count=int(len(airports)),
                                   message="Airport reference subset loaded from cached OurAirports download.",
                                   details={"retrieved_at_utc": ap_meta.get("retrieved_at_utc")}))

    from app.services.scenario_engine.prebuilt import seed_prebuilt_scenarios

    with session_scope(settings.database_url) as s:
        seed_prebuilt_scenarios(s, settings, world.edges, pos)

    # ---- manifest ------------------------------------------------------------
    upsert_entry("synthetic_demo_observations", {
        "source_name": "Sky Force synthetic generator", "dataset_id": ds, "kind": "synthetic",
        "file": str(raw_obs_path.relative_to(settings.data_dir)), "format": "parquet",
        "sha256": file_sha256(raw_obs_path), "record_count_raw": int(len(raw)), "record_count_clean": int(len(clean)),
        "date_range_utc": rep["time_range_utc"], "temporal_resolution": f"{settings.demo_sample_seconds} s",
        "fields": list(raw.columns), "units": {"altitude_m": "m", "ground_speed_mps": "m/s", "heading_deg": "deg", "vertical_rate_mps": "m/s"},
        "licence": "Generated by this project (MIT)", "seed": settings.demo_seed,
    })
    upsert_entry("synthetic_demo_weather", {
        "source_name": "Sky Force synthetic weather field", "dataset_id": ds, "kind": "synthetic",
        "record_count": int(len(world.weather)), "temporal_resolution": "1 h", "spatial_resolution": f"{grid.deg} deg grid cells (corridor only)",
        "units": {"precipitation_mm": "mm (preceding hour)", "wind_speed_10m_ms": "m/s", "cloud_cover_pct": "%"},
        "note": "Synthetic surface-style fields. NOT flight-level observations.",
    })
    upsert_entry("ourairports_subset", {
        "source_name": "OurAirports", "url": ap_meta.get("url"), "kind": "real_reference",
        "retrieved_at_utc": ap_meta.get("retrieved_at_utc"), "record_count": int(len(airports)),
        "sha256_full_file": ap_meta.get("full_file_sha256"), "licence": ap_meta.get("licence"),
    })
    summary = {
        "dataset": ds, "observations_raw": int(len(raw)), "observations_clean": int(len(clean)),
        "tracks": int(len(tracks)), "airports": int(len(airports)), "waypoints": int(len(world.waypoints)),
        "edges": int(len(world.edges)), "corridor_cells": len(corridor), "congestion_rows": int(len(agg)),
        "eta_traversals": int(len(trav)), "thresholds": th.to_dict(), "seconds": round(time.perf_counter() - t0, 1),
    }
    log_event(logger, "bootstrap complete", **summary)
    return summary


def processed_path(settings: Settings, name: str) -> Path:
    return settings.data_dir / "processed" / name


def _unused() -> None:  # pragma: no cover - keeps numpy import explicit for type checkers
    np.zeros(1)
