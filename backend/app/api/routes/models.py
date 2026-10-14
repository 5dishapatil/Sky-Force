"""Machine Learning Model metadata, metrics, and feature introspection endpoints."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from fastapi import APIRouter

from app.api.state import get_state
from app.core.config import get_settings

router = APIRouter(prefix="/models", tags=["Machine Learning"])


@router.get("/status")
def get_models_status() -> dict[str, Any]:
    state = get_state()
    settings = get_settings()

    congestion_info = None
    if state.congestion_model:
        m = state.congestion_model.metadata
        feats = m.get("feature_schema", {}).get("features", [])
        sha = m.get("sha256", "")
        congestion_info = {
            "name": m.get("model_name", "random_forest"),
            "kind": state.congestion_model.kind,
            "version": state.congestion_model.version,
            "task": m.get("task"),
            "target_definition": m.get("target_definition"),
            "metrics": m.get("metrics", {}),
            "feature_names": feats,
            "feature_count": len(feats),
            "sha256": sha[:16] + "..." if sha else "",
            "is_loaded": True,
        }

    eta_info = None
    if state.eta_model:
        m = state.eta_model.metadata
        feats = m.get("feature_schema", {}).get("features", [])
        sha = m.get("sha256", "")
        eta_info = {
            "name": m.get("model_name", "random_forest"),
            "kind": state.eta_model.kind,
            "version": state.eta_model.version,
            "task": m.get("task"),
            "target_definition": m.get("target_definition"),
            "metrics": m.get("metrics", {}),
            "feature_names": feats,
            "feature_count": len(feats),
            "sha256": sha[:16] + "..." if sha else "",
            "is_loaded": True,
        }

    # Load summary if present
    summary_path = settings.reports_dir / "training_summary.json"
    summary = {}
    if summary_path.exists():
        try:
            summary = json.loads(summary_path.read_text())
        except Exception:
            pass

    return {
        "status": "operational",
        "congestion_model": congestion_info,
        "eta_model": eta_info,
        "training_summary": summary,
        "disclaimer": "Academic ML models for spatial airspace density & travel-time proxies. Not for tactical ATC separation.",
    }


@router.get("/metrics")
def get_model_evaluation_metrics() -> dict[str, Any]:
    settings = get_settings()
    rep_dir = settings.reports_dir

    congestion_metrics = {}
    c_path = rep_dir / "congestion_metrics.json"
    if c_path.exists():
        try:
            congestion_metrics = json.loads(c_path.read_text())
        except Exception:
            pass

    eta_metrics = {}
    e_path = rep_dir / "eta_metrics.json"
    if e_path.exists():
        try:
            eta_metrics = json.loads(e_path.read_text())
        except Exception:
            pass

    return {
        "congestion": congestion_metrics,
        "eta": eta_metrics,
    }


@router.get("/feature-importance")
def get_feature_importance() -> dict[str, Any]:
    state = get_state()
    out: dict[str, Any] = {"congestion": [], "eta": []}

    # Extract feature importances if tree models are loaded
    if state.congestion_model:
        try:
            pipe = state.congestion_model.pipeline
            clf = pipe.named_steps.get("clf")
            feat_names = state.congestion_model.metadata.get("feature_schema", {}).get("features", [])
            if hasattr(clf, "feature_importances_"):
                importances = clf.feature_importances_
                out["congestion"] = sorted(
                    [
                        {"feature": str(f), "importance": round(float(imp), 4)}
                        for f, imp in zip(feat_names, importances)
                    ],
                    key=lambda x: x["importance"],
                    reverse=True,
                )
        except Exception:
            pass

    if state.eta_model:
        try:
            pipe = state.eta_model.pipeline
            reg = pipe.named_steps.get("reg")
            if hasattr(reg, "feature_importances_"):
                importances = reg.feature_importances_
                try:
                    pre = pipe.named_steps.get("pre")
                    feat_names = list(pre.get_feature_names_out())
                except Exception:
                    feat_names = [f"feat_{i}" for i in range(len(importances))]

                out["eta"] = sorted(
                    [
                        {"feature": str(f).replace("cat__", "").replace("num__", ""), "importance": round(float(imp), 4)}
                        for f, imp in zip(feat_names, importances)
                    ],
                    key=lambda x: x["importance"],
                    reverse=True,
                )[:25]
        except Exception:
            pass

    return out


@router.get("/evaluation-summary")
def get_evaluation_summary() -> dict[str, Any]:
    """Retrieve structured evaluation report tables, error percentiles, confusion matrices, and model comparison data."""
    import pandas as pd
    from app.services.models.reporting import generate_all_reports

    settings = get_settings()
    rep_dir = settings.reports_dir

    # Auto-generate if structured reports do not exist yet
    if not (rep_dir / "congestion_classification_report.csv").exists() or not (rep_dir / "eta_metrics_summary.csv").exists():
        try:
            generate_all_reports(settings, include_learning_curves=False)
        except Exception as e:
            pass

    def _read_csv(filename: str) -> list[dict[str, Any]]:
        p = rep_dir / filename
        if p.exists():
            try:
                df = pd.read_csv(p)
                return df.where(pd.notna(df), None).to_dict(orient="records")
            except Exception:
                return []
        return []

    # Load summary json
    summary_path = rep_dir / "training_summary.json"
    summary_data = {}
    if summary_path.exists():
        try:
            summary_data = json.loads(summary_path.read_text())
        except Exception:
            pass

    return {
        "status": "success",
        "generated_at_utc": summary_data.get("generated_at_utc") or datetime.now(timezone.utc).isoformat(),
        "training_summary": summary_data,
        "congestion": {
            "summary": _read_csv("congestion_metrics_summary.csv"),
            "class_report": _read_csv("congestion_classification_report.csv"),
            "confusion_matrix": _read_csv("congestion_confusion_matrix.csv"),
            "confusion_matrix_norm": _read_csv("congestion_confusion_matrix_normalized.csv"),
            "feature_importance": _read_csv("congestion_feature_importance.csv"),
            "learning_curve": _read_csv("congestion_learning_curve_data.csv"),
            "model_comparison": _read_csv("congestion_model_comparison.csv"),
        },
        "eta": {
            "summary": _read_csv("eta_metrics_summary.csv"),
            "error_summary": _read_csv("eta_error_summary.csv"),
            "error_by_range": _read_csv("eta_error_by_range.csv"),
            "feature_importance": _read_csv("eta_feature_importance.csv"),
            "learning_curve": _read_csv("eta_learning_curve_data.csv"),
            "model_comparison": _read_csv("eta_model_comparison.csv"),
            "actual_vs_predicted_sample": _read_csv("eta_actual_vs_predicted.csv")[:50],
        },
        "consolidated": _read_csv("model_metrics_summary.csv"),
        "html_report_available": (rep_dir / "model_evaluation_report.html").exists(),
    }


@router.get("/reports")
def list_evaluation_reports() -> dict[str, Any]:
    """List all available report files (CSV, JSON, HTML) with metadata and safe download links."""
    settings = get_settings()
    rep_dir = settings.reports_dir
    files = []
    if rep_dir.exists():
        for f in sorted(rep_dir.glob("*")):
            if f.is_file() and f.suffix.lower() in (".csv", ".json", ".html"):
                files.append({
                    "filename": f.name,
                    "extension": f.suffix.lower().replace(".", ""),
                    "size_bytes": f.stat().st_size,
                    "download_url": f"/api/models/reports/{f.name}",
                })
    return {"reports": files, "count": len(files)}


@router.get("/reports/{filename}")
def download_evaluation_report(filename: str):
    """Safely download or view an exported report file with strict path traversal validation."""
    from fastapi.responses import FileResponse
    from fastapi import HTTPException

    settings = get_settings()
    rep_dir = settings.reports_dir.resolve()

    # Security: whitelist characters and allowed extensions
    if not filename or any(c in filename for c in ("..", "/", "\\", "\0")):
        raise HTTPException(status_code=400, detail="Invalid filename")

    allowed_exts = {".csv", ".json", ".html"}
    target = (rep_dir / filename).resolve()

    if target.suffix.lower() not in allowed_exts:
        raise HTTPException(status_code=400, detail="File format not permitted")

    # Path traversal verification
    if not str(target).startswith(str(rep_dir)):
        raise HTTPException(status_code=403, detail="Access denied")

    if not target.exists():
        raise HTTPException(status_code=404, detail="Report file not found")

    media_types = {
        ".csv": "text/csv",
        ".json": "application/json",
        ".html": "text/html",
    }
    media_type = media_types.get(target.suffix.lower(), "application/octet-stream")
    return FileResponse(path=target, media_type=media_type, filename=filename)


@router.post("/generate-reports")
def trigger_generate_reports(include_learning_curves: bool = True) -> dict[str, Any]:
    """Trigger complete regeneration of all structured evaluation reports on demand."""
    from app.services.models.reporting import generate_all_reports

    settings = get_settings()
    result = generate_all_reports(settings, include_learning_curves=include_learning_curves)
    return {
        "status": "success",
        "message": "Evaluation reports regenerated successfully",
        "html_report": result.get("html_report"),
    }

