"""Training orchestration: processed files -> features -> models -> artifacts/reports/DB."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import pandas as pd
from sqlalchemy import update

from app.core.config import Settings
from app.core.logging import get_logger, log_event
from app.db import models as m
from app.db.session import session_scope
from app.services.features.congestion import Thresholds, build_feature_frame
from app.services.features.eta import build_eta_features
from app.services.features.splits import demo_boundaries
from app.services.geospatial.grid import grid_from_settings
from app.services.models.registry import save_artifact
from app.services.models.training import train_congestion, train_eta

logger = get_logger(__name__)


def load_processed(settings: Settings) -> dict[str, Any]:
    p = settings.data_dir / "processed"
    s = settings.data_dir / "synthetic"
    needed = [p / "congestion_agg.parquet", p / "congestion_thresholds.json", p / "eta_traversals.parquet",
              s / "weather_synthetic.parquet", s / "edges.csv", s / "waypoints.csv"]
    missing = [str(x) for x in needed if not x.exists()]
    if missing:
        raise FileNotFoundError(f"Processed data missing ({missing}). Run `python scripts/bootstrap_demo.py` first.")
    return {
        "agg": pd.read_parquet(p / "congestion_agg.parquet"),
        "thresholds": json.loads((p / "congestion_thresholds.json").read_text()),
        "traversals": pd.read_parquet(p / "eta_traversals.parquet"),
        "weather": pd.read_parquet(s / "weather_synthetic.parquet"),
        "edges": pd.read_csv(s / "edges.csv"),
        "waypoints": pd.read_csv(s / "waypoints.csv"),
    }


def run_training(settings: Settings, which: tuple[str, ...] = ("congestion", "eta")) -> dict[str, Any]:
    from app.services.ingestion.bootstrap import airports_frame

    d = load_processed(settings)
    grid = grid_from_settings(settings)
    bounds = demo_boundaries(settings)
    seed = settings.demo_seed
    reports = settings.reports_dir
    reports.mkdir(parents=True, exist_ok=True)
    airports, _ = airports_frame()
    nodes = pd.concat([airports[["node_id", "latitude", "longitude"]], d["waypoints"][["node_id", "latitude", "longitude"]]])
    pos = {r.node_id: (r.latitude, r.longitude) for r in nodes.itertuples()}
    corridor = sorted({c for e in d["edges"].itertuples() for c in grid.cells_along(*pos[e.source_node], *pos[e.target_node])})
    summary: dict[str, Any] = {}
    data_kind = "synthetic"
    common = {"data_kind": data_kind, "dataset_id": settings.demo_dataset_id,
              "data_notice": "Trained on SYNTHETIC demonstration data. Metrics are software-demonstration figures, "
                             "NOT evidence of real-world aviation accuracy.",
              "trained_at_utc": datetime.now(timezone.utc).isoformat(),
              "source_manifest": "data/source_manifest.json"}

    if "congestion" in which:
        th_d = d["thresholds"]
        th = Thresholds(th_d["low_max"], th_d["medium_max"], th_d["method"])
        frame = build_feature_frame(d["agg"], d["weather"], grid, corridor, bounds.start, bounds.end, settings.window_minutes)
        res = train_congestion(frame, bounds, th, settings.window_minutes, seed)
        version, path = save_artifact("congestion", res["pipeline"], {**res["metadata"], **common})
        res["test_predictions"].to_csv(path / "test_predictions.csv", index=False)
        (reports / "congestion_metrics.json").write_text(json.dumps(res["metadata"]["metrics"], indent=2))
        res["test_predictions"].to_csv(reports / "congestion_test_predictions.csv", index=False)
        _register(settings, "congestion", version, path, res["metadata"], common)
        summary["congestion"] = {"version": version, "model": res["metadata"]["model_name"],
                                 "test": {k: res["metadata"]["selected_test_metrics"][k] for k in ("accuracy", "balanced_accuracy", "macro_f1")}}
        log_event(logger, "congestion model trained", **summary["congestion"])

    if "eta" in which:
        counts = d["agg"][["cell_id", "window_start_utc", "aircraft_count"]]
        feats = build_eta_features(d["traversals"], d["edges"], set(airports.node_id), d["weather"], counts, grid, pos,
                                   settings.window_minutes)
        feats.to_parquet(settings.data_dir / "processed" / "eta_features.parquet", index=False)
        res = train_eta(feats, bounds, seed, settings.heuristic_cruise_speed_kmh)
        version, path = save_artifact("eta", res["pipeline"], {**res["metadata"], **common})
        res["test_predictions"].to_csv(path / "test_predictions.csv", index=False)
        (reports / "eta_metrics.json").write_text(json.dumps(res["metadata"]["metrics"], indent=2))
        res["test_predictions"].to_csv(reports / "eta_test_predictions.csv", index=False)
        _register(settings, "eta", version, path, res["metadata"], common)
        summary["eta"] = {"version": version, "model": res["metadata"]["model_name"],
                          "test": {k: res["metadata"]["selected_test_metrics"][k] for k in ("mae_min", "rmse_min", "r2")}}
        log_event(logger, "eta model trained", **summary["eta"])
    (reports / "training_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def _register(settings: Settings, kind: str, version: str, path, meta: dict, common: dict) -> None:  # noqa: ANN001
    with session_scope(settings.database_url) as s:
        s.execute(update(m.ModelArtifactMetadata).where(m.ModelArtifactMetadata.model_kind == kind).values(is_active=False))
        s.add(m.ModelArtifactMetadata(
            model_kind=kind, version=version, path=str(path), trained_at=datetime.now(timezone.utc),
            data_kind=common["data_kind"], dataset_id=common["dataset_id"], is_active=True,
            metadata_json={"model_name": meta["model_name"], "selected_test_metrics": meta["selected_test_metrics"],
                           "splits": meta["splits"]},
        ))
