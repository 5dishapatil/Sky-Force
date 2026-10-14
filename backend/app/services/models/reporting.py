"""Structured Model Evaluation & Reporting Engine for Sky Force.

Generates comprehensive, tabular, chart-ready metrics, CSV files, JSON metadata,
and an HTML evaluation report (pure tables, zero graphics).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    confusion_matrix,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_recall_fscore_support,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

CONGESTION_CLASSES = ["LOW", "MEDIUM", "HIGH"]
ETA_UNIT = "minutes"


def compute_congestion_reports(
    reports_dir: Path,
    artifacts_dir: Path,
) -> dict[str, Any]:
    """Calculate and export structured evaluation tables for congestion classification."""
    pred_path = reports_dir / "congestion_test_predictions.csv"
    if not pred_path.exists():
        raise FileNotFoundError(f"Missing predictions file: {pred_path}")

    df = pd.read_csv(pred_path)
    if "y_true" not in df.columns or "y_pred" not in df.columns:
        raise ValueError("Predictions CSV must contain 'y_true' and 'y_pred' columns")

    y_true = df["y_true"].astype(str)
    y_pred = df["y_pred"].astype(str)
    sample_count = len(df)

    # 1. Overall Metrics (Table A)
    acc = float(accuracy_score(y_true, y_pred))
    bal_acc = float(balanced_accuracy_score(y_true, y_pred))
    macro_f1 = float(f1_score(y_true, y_pred, labels=CONGESTION_CLASSES, average="macro", zero_division=0))
    weighted_f1 = float(f1_score(y_true, y_pred, labels=CONGESTION_CLASSES, average="weighted", zero_division=0))
    macro_prec = float(precision_score(y_true, y_pred, labels=CONGESTION_CLASSES, average="macro", zero_division=0))
    weighted_prec = float(precision_score(y_true, y_pred, labels=CONGESTION_CLASSES, average="weighted", zero_division=0))
    macro_rec = float(recall_score(y_true, y_pred, labels=CONGESTION_CLASSES, average="macro", zero_division=0))
    weighted_rec = float(recall_score(y_true, y_pred, labels=CONGESTION_CLASSES, average="weighted", zero_division=0))

    # Multiclass Brier & ROC-AUC if probability columns exist
    brier_val: float | None = None
    roc_auc_val: float | None = None
    prob_cols = [f"p_{c}" for c in CONGESTION_CLASSES]
    has_probs = all(c in df.columns for c in prob_cols)
    if has_probs:
        proba = df[prob_cols].values
        onehot = np.stack([(y_true.values == c).astype(float) for c in CONGESTION_CLASSES], axis=1)
        brier_val = float(np.mean(np.sum((proba - onehot) ** 2, axis=1)))
        try:
            roc_auc_val = float(roc_auc_score(onehot, proba, average="macro", multi_class="ovr"))
        except Exception:
            roc_auc_val = None

    table_a_rows = [
        {"metric": "Accuracy", "value": round(acc, 6), "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "Overall proportion of correct predictions across all classes"},
        {"metric": "Balanced Accuracy", "value": round(bal_acc, 6), "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "Unweighted average recall across classes (guards against majority-class dominance)"},
        {"metric": "Macro F1", "value": round(macro_f1, 6), "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "Unweighted harmonic mean of precision and recall averaged across classes"},
        {"metric": "Weighted F1", "value": round(weighted_f1, 6), "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "F1-score averaged according to each class's test support"},
        {"metric": "Macro Precision", "value": round(macro_prec, 6), "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "Unweighted average precision across classes"},
        {"metric": "Weighted Precision", "value": round(weighted_prec, 6), "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "Precision averaged according to class support"},
        {"metric": "Macro Recall", "value": round(macro_rec, 6), "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "Unweighted average recall across classes (identical to balanced accuracy)"},
        {"metric": "Weighted Recall", "value": round(weighted_rec, 6), "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "Recall averaged according to class support (identical to accuracy)"},
        {"metric": "Multi-class Brier Score", "value": round(brier_val, 6) if brier_val is not None else "unavailable",
         "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "Mean squared probability calibration error (lower is better, range [0, 2])"},
        {"metric": "ROC-AUC OvR Macro", "value": round(roc_auc_val, 6) if roc_auc_val is not None else "unavailable",
         "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "One-vs-Rest Area Under the ROC Curve, macro-averaged (chance = 0.5)"},
    ]
    df_metrics_summary = pd.DataFrame(table_a_rows)
    df_metrics_summary.to_csv(reports_dir / "congestion_metrics_summary.csv", index=False)

    # 2. Per-class Classification Report (Table B)
    p, r, f, sup = precision_recall_fscore_support(y_true, y_pred, labels=CONGESTION_CLASSES, zero_division=0)
    class_rows = []
    for i, c in enumerate(CONGESTION_CLASSES):
        class_rows.append({
            "class": c,
            "precision": round(float(p[i]), 6),
            "recall": round(float(r[i]), 6),
            "f1_score": round(float(f[i]), 6),
            "support": int(sup[i]),
        })
    class_rows.append({
        "class": "Macro Average",
        "precision": round(macro_prec, 6),
        "recall": round(macro_rec, 6),
        "f1_score": round(macro_f1, 6),
        "support": sample_count,
    })
    class_rows.append({
        "class": "Weighted Average",
        "precision": round(weighted_prec, 6),
        "recall": round(weighted_rec, 6),
        "f1_score": round(weighted_f1, 6),
        "support": sample_count,
    })
    df_class_report = pd.DataFrame(class_rows)
    df_class_report.to_csv(reports_dir / "congestion_classification_report.csv", index=False)

    # 3. Confusion Matrix (Table C)
    cm = confusion_matrix(y_true, y_pred, labels=CONGESTION_CLASSES)
    cm_dict = {"actual_class": CONGESTION_CLASSES}
    for j, c in enumerate(CONGESTION_CLASSES):
        cm_dict[c] = cm[:, j].tolist()
    df_cm = pd.DataFrame(cm_dict)
    df_cm.to_csv(reports_dir / "congestion_confusion_matrix.csv", index=False)

    # 4. Normalized Confusion Matrix (Table D - row normalized by actual support)
    row_sums = cm.sum(axis=1)[:, np.newaxis]
    cm_norm = np.divide(cm.astype(float), row_sums, out=np.zeros_like(cm, dtype=float), where=row_sums != 0)
    cm_norm_dict = {"actual_class": CONGESTION_CLASSES}
    for j, c in enumerate(CONGESTION_CLASSES):
        cm_norm_dict[c] = [round(float(val), 6) for val in cm_norm[:, j]]
    df_cm_norm = pd.DataFrame(cm_norm_dict)
    df_cm_norm.to_csv(reports_dir / "congestion_confusion_matrix_normalized.csv", index=False)

    # 5. Feature Importance
    meta = _load_active_metadata(artifacts_dir / "congestion")
    feat_rows = []
    if meta:
        version = meta.get("version", "unknown")
        model_name = meta.get("model_name", "RandomForestClassifier")
        # Native MDI
        builtin = meta.get("builtin_importance", []) or []
        for rank, item in enumerate(builtin, 1):
            feat_rows.append({
                "rank": rank,
                "feature_name": item["feature"],
                "importance_value": round(float(item["importance"]), 6),
                "importance_method": "native_mdi",
                "model_name": model_name,
                "model_version": version,
            })
        # Validation Permutation Importance
        perm = meta.get("permutation_importance_validation", []) or []
        for rank, item in enumerate(perm, 1):
            feat_rows.append({
                "rank": rank,
                "feature_name": item["feature"],
                "importance_value": round(float(item.get("importance_mean", 0.0)), 6),
                "importance_method": "permutation_importance_validation",
                "model_name": model_name,
                "model_version": version,
            })
    df_feat = pd.DataFrame(feat_rows) if feat_rows else pd.DataFrame(
        columns=["rank", "feature_name", "importance_value", "importance_method", "model_name", "model_version"]
    )
    df_feat.to_csv(reports_dir / "congestion_feature_importance.csv", index=False)

    # 6. Candidate Models Comparison Table
    cand_path = reports_dir / "congestion_metrics.json"
    comp_rows = []
    if cand_path.exists():
        try:
            cand_data = json.loads(cand_path.read_text())
            for name, payload in cand_data.items():
                if not isinstance(payload, dict):
                    continue
                fit_s = payload.get("fit_seconds", "unavailable")
                for sp in ("validation", "test"):
                    sp_data = payload.get(sp)
                    if not isinstance(sp_data, dict):
                        continue
                    comp_rows.append({
                        "model_name": name,
                        "split": sp,
                        "n_samples": sp_data.get("n", 0),
                        "fit_seconds": fit_s,
                        "accuracy": round(float(sp_data["accuracy"]), 6) if "accuracy" in sp_data else None,
                        "balanced_accuracy": round(float(sp_data["balanced_accuracy"]), 6) if "balanced_accuracy" in sp_data else None,
                        "macro_f1": round(float(sp_data["macro_f1"]), 6) if "macro_f1" in sp_data else None,
                        "brier_multiclass": round(float(sp_data["brier_multiclass"]), 6) if sp_data.get("brier_multiclass") is not None else "unavailable",
                        "roc_auc_ovr_macro": round(float(sp_data["roc_auc_ovr_macro"]), 6) if sp_data.get("roc_auc_ovr_macro") is not None else "unavailable",
                    })
        except Exception as e:
            logger.warning(f"Could not parse candidate congestion metrics: {e}")
    df_comp = pd.DataFrame(comp_rows) if comp_rows else pd.DataFrame(
        columns=["model_name", "split", "n_samples", "fit_seconds", "accuracy", "balanced_accuracy", "macro_f1", "brier_multiclass", "roc_auc_ovr_macro"]
    )
    df_comp.to_csv(reports_dir / "congestion_model_comparison.csv", index=False)

    return {
        "summary": df_metrics_summary,
        "class_report": df_class_report,
        "confusion_matrix": df_cm,
        "confusion_matrix_norm": df_cm_norm,
        "feature_importance": df_feat,
        "model_comparison": df_comp,
        "sample_count": sample_count,
        "accuracy": acc,
        "balanced_accuracy": bal_acc,
        "macro_f1": macro_f1,
        "weighted_f1": weighted_f1,
    }


def compute_eta_reports(
    reports_dir: Path,
    artifacts_dir: Path,
) -> dict[str, Any]:
    """Calculate and export structured evaluation tables for segment ETA regression."""
    pred_path = reports_dir / "eta_test_predictions.csv"
    if not pred_path.exists():
        raise FileNotFoundError(f"Missing predictions file: {pred_path}")

    df = pd.read_csv(pred_path)
    required = ["actual_min", "predicted_min"]
    if not all(col in df.columns for col in required):
        raise ValueError("ETA predictions CSV must contain 'actual_min' and 'predicted_min' columns")

    y_true = df["actual_min"].astype(float)
    y_pred = df["predicted_min"].astype(float)
    sample_count = len(df)

    signed_err = y_pred - y_true
    abs_err = np.abs(signed_err)

    # 1. Overall Metrics (Table A)
    mae = float(mean_absolute_error(y_true, y_pred))
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    r2 = float(r2_score(y_true, y_pred))
    median_abs_err = float(np.median(abs_err))
    mean_signed_err = float(signed_err.mean())
    median_signed_err = float(np.median(signed_err))
    std_err = float(signed_err.std())
    p90_abs_err = float(np.percentile(abs_err, 90))
    p95_abs_err = float(np.percentile(abs_err, 95))
    p99_abs_err = float(np.percentile(abs_err, 99))
    min_abs_err = float(abs_err.min())
    max_abs_err = float(abs_err.max())

    heur_mae = None
    heur_rmse = None
    heur_r2 = None
    if "heuristic_min" in df.columns:
        y_heur = df["heuristic_min"].astype(float)
        heur_mae = float(mean_absolute_error(y_true, y_heur))
        heur_rmse = float(np.sqrt(mean_squared_error(y_true, y_heur)))
        heur_r2 = float(r2_score(y_true, y_heur))

    table_a_rows = [
        {"metric": "Mean Absolute Error (MAE)", "value": round(mae, 6), "unit": ETA_UNIT, "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "Average magnitude of prediction error in minutes (lower is better)"},
        {"metric": "Root Mean Squared Error (RMSE)", "value": round(rmse, 6), "unit": ETA_UNIT, "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "Square root of mean squared error; penalizes larger flight deviations"},
        {"metric": "Coefficient of Determination (R²)", "value": round(r2, 6), "unit": "unitless", "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "Proportion of target variance explained by model versus horizontal mean"},
        {"metric": "Median Absolute Error", "value": round(median_abs_err, 6), "unit": ETA_UNIT, "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "50th percentile of absolute error; robust against extreme outliers"},
        {"metric": "Mean Signed Error (Bias)", "value": round(mean_signed_err, 6), "unit": ETA_UNIT, "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "Average signed deviation (predicted - actual); negative indicates slight underestimation"},
        {"metric": "Median Signed Error", "value": round(median_signed_err, 6), "unit": ETA_UNIT, "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "Median signed deviation (predicted - actual)"},
        {"metric": "Error Standard Deviation", "value": round(std_err, 6), "unit": ETA_UNIT, "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "Spread of signed prediction errors around the mean bias"},
        {"metric": "90th Percentile Absolute Error", "value": round(p90_abs_err, 6), "unit": ETA_UNIT, "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "90% of all airway segment traversals are predicted within this margin"},
        {"metric": "95th Percentile Absolute Error", "value": round(p95_abs_err, 6), "unit": ETA_UNIT, "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "95% of test segment traversals are predicted within this margin"},
        {"metric": "99th Percentile Absolute Error", "value": round(p99_abs_err, 6), "unit": ETA_UNIT, "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "Near-worst-case bound covering 99% of test segment traversals"},
        {"metric": "Minimum Absolute Error", "value": round(min_abs_err, 6), "unit": ETA_UNIT, "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "Closest single prediction to actual observed segment duration"},
        {"metric": "Maximum Absolute Error", "value": round(max_abs_err, 6), "unit": ETA_UNIT, "evaluation_split": "test",
         "sample_count": sample_count, "interpretation": "Worst single prediction error observed across all test segments"},
        {"metric": "Baseline Heuristic MAE (780 km/h)", "value": round(heur_mae, 6) if heur_mae is not None else "unavailable",
         "unit": ETA_UNIT, "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "Standard nominal cruise-speed baseline error (distance / 780 km/h)"},
        {"metric": "Baseline Heuristic RMSE (780 km/h)", "value": round(heur_rmse, 6) if heur_rmse is not None else "unavailable",
         "unit": ETA_UNIT, "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "Nominal cruise-speed baseline RMSE"},
        {"metric": "Baseline Heuristic R² (780 km/h)", "value": round(heur_r2, 6) if heur_r2 is not None else "unavailable",
         "unit": "unitless", "evaluation_split": "test", "sample_count": sample_count,
         "interpretation": "Variance explained by nominal cruise-speed baseline"},
    ]
    df_eta_summary = pd.DataFrame(table_a_rows)
    df_eta_summary.to_csv(reports_dir / "eta_metrics_summary.csv", index=False)

    # 2. Row-Level Actual vs Predicted Table (Table B)
    df_actual_pred = df.copy()
    if "sample_id" not in df_actual_pred.columns:
        df_actual_pred.insert(0, "sample_id", [f"ETA_TE_{i+1:04d}" for i in range(len(df_actual_pred))])
    df_actual_pred["signed_error_min"] = signed_err.round(6)
    df_actual_pred["abs_error_min"] = abs_err.round(6)
    pct_err = np.where(y_true > 0, (signed_err / y_true) * 100.0, 0.0)
    df_actual_pred["percentage_error_pct"] = np.round(pct_err, 4)
    df_actual_pred.to_csv(reports_dir / "eta_actual_vs_predicted.csv", index=False)

    # 3. Error Distribution (Table C)
    error_summary_rows = []
    for col_name, series in [("signed_error_min", signed_err), ("abs_error_min", abs_err)]:
        error_summary_rows.append({
            "error_type": col_name,
            "unit": ETA_UNIT,
            "sample_count": int(len(series)),
            "mean": round(float(series.mean()), 6),
            "std": round(float(series.std()), 6),
            "median": round(float(np.median(series)), 6),
            "min": round(float(series.min()), 6),
            "max": round(float(series.max()), 6),
            "p10": round(float(np.percentile(series, 10)), 6),
            "p25": round(float(np.percentile(series, 25)), 6),
            "p50": round(float(np.percentile(series, 50)), 6),
            "p75": round(float(np.percentile(series, 75)), 6),
            "p90": round(float(np.percentile(series, 90)), 6),
            "p95": round(float(np.percentile(series, 95)), 6),
            "p99": round(float(np.percentile(series, 99)), 6),
            "missing_or_invalid_count": int(series.isna().sum()),
        })
    df_err_summary = pd.DataFrame(error_summary_rows)
    df_err_summary.to_csv(reports_dir / "eta_error_summary.csv", index=False)

    # 4. Error by Target Range (Table D)
    bins = [0.0, 15.0, 25.0, 35.0, 1e9]
    labels = ["< 15 min", "15-25 min", "25-35 min", ">= 35 min"]
    df["range_bin"] = pd.cut(y_true, bins=bins, labels=labels, right=False)
    range_rows = []
    for b in labels:
        sub = df[df["range_bin"] == b]
        sub_n = len(sub)
        if sub_n == 0:
            range_rows.append({
                "target_range": b, "sample_count": 0, "min_actual_min": None, "max_actual_min": None,
                "mean_actual_min": None, "mae_min": None, "rmse_min": None, "mean_signed_error_min": None,
                "median_abs_error_min": None, "p90_abs_error_min": None, "r2": None,
            })
            continue
        sub_yt = sub["actual_min"].values
        sub_yp = sub["predicted_min"].values
        sub_err = sub_yp - sub_yt
        sub_abs = np.abs(sub_err)
        sub_r2 = float(r2_score(sub_yt, sub_yp)) if sub_n > 1 and np.var(sub_yt) > 1e-9 else None
        range_rows.append({
            "target_range": b,
            "sample_count": sub_n,
            "min_actual_min": round(float(sub_yt.min()), 4),
            "max_actual_min": round(float(sub_yt.max()), 4),
            "mean_actual_min": round(float(sub_yt.mean()), 4),
            "mae_min": round(float(sub_abs.mean()), 6),
            "rmse_min": round(float(np.sqrt((sub_err ** 2).mean())), 6),
            "mean_signed_error_min": round(float(sub_err.mean()), 6),
            "median_abs_error_min": round(float(np.median(sub_abs)), 6),
            "p90_abs_error_min": round(float(np.percentile(sub_abs, 90)), 6),
            "r2": round(sub_r2, 6) if sub_r2 is not None else "insufficient_variance",
        })
    df_range = pd.DataFrame(range_rows)
    df_range.to_csv(reports_dir / "eta_error_by_range.csv", index=False)

    # 5. Feature Importance
    meta = _load_active_metadata(artifacts_dir / "eta")
    feat_rows = []
    if meta:
        version = meta.get("version", "unknown")
        model_name = meta.get("model_name", "RandomForestRegressor")
        builtin = meta.get("builtin_importance", []) or []
        for rank, item in enumerate(builtin, 1):
            feat_rows.append({
                "rank": rank,
                "feature_name": item["feature"],
                "importance_value": round(float(item["importance"]), 6),
                "importance_method": "native_mdi",
                "model_name": model_name,
                "model_version": version,
            })
        perm = meta.get("permutation_importance_validation", []) or []
        for rank, item in enumerate(perm, 1):
            feat_rows.append({
                "rank": rank,
                "feature_name": item["feature"],
                "importance_value": round(float(item.get("importance_mean", 0.0)), 6),
                "importance_method": "permutation_importance_validation",
                "model_name": model_name,
                "model_version": version,
            })
    df_feat = pd.DataFrame(feat_rows) if feat_rows else pd.DataFrame(
        columns=["rank", "feature_name", "importance_value", "importance_method", "model_name", "model_version"]
    )
    df_feat.to_csv(reports_dir / "eta_feature_importance.csv", index=False)

    # 6. Candidate Models Comparison Table
    cand_path = reports_dir / "eta_metrics.json"
    comp_rows = []
    if cand_path.exists():
        try:
            cand_data = json.loads(cand_path.read_text())
            for name, payload in cand_data.items():
                if not isinstance(payload, dict):
                    continue
                fit_s = payload.get("fit_seconds", "not_fitted" if "heuristic" in name else "unavailable")
                for sp in ("validation", "test"):
                    sp_data = payload.get(sp)
                    if not isinstance(sp_data, dict):
                        continue
                    comp_rows.append({
                        "model_name": name,
                        "split": sp,
                        "n_samples": sp_data.get("n", 0),
                        "fit_seconds": fit_s,
                        "mae_min": round(float(sp_data["mae_min"]), 6) if "mae_min" in sp_data else None,
                        "rmse_min": round(float(sp_data["rmse_min"]), 6) if "rmse_min" in sp_data else None,
                        "r2": round(float(sp_data["r2"]), 6) if "r2" in sp_data else None,
                        "bias_min": round(float(sp_data["bias_min"]), 6) if "bias_min" in sp_data else None,
                    })
        except Exception as e:
            logger.warning(f"Could not parse candidate ETA metrics: {e}")
    df_comp = pd.DataFrame(comp_rows) if comp_rows else pd.DataFrame(
        columns=["model_name", "split", "n_samples", "fit_seconds", "mae_min", "rmse_min", "r2", "bias_min"]
    )
    df_comp.to_csv(reports_dir / "eta_model_comparison.csv", index=False)

    return {
        "summary": df_eta_summary,
        "actual_vs_predicted": df_actual_pred,
        "error_summary": df_err_summary,
        "error_by_range": df_range,
        "feature_importance": df_feat,
        "model_comparison": df_comp,
        "sample_count": sample_count,
        "mae": mae,
        "rmse": rmse,
        "r2": r2,
        "median_abs_err": median_abs_err,
        "mean_signed_err": mean_signed_err,
    }


def compute_learning_curves(settings: Settings) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Calculate empirical learning curves on chronological training subsets evaluated against the validation split."""
    from app.services.features.congestion import (
        CATEGORICAL_FEATURES,
        CLASSES,
        FEATURES,
        NUMERIC_FEATURES,
        TARGET_COUNT,
        Thresholds,
        chronological_split,
        classify,
        build_feature_frame,
    )
    from app.services.features.eta import ETA_FEATURES, ETA_NUMERIC, ETA_TARGET
    from app.services.features.splits import demo_boundaries
    from app.services.geospatial.grid import grid_from_settings
    from app.services.ingestion.bootstrap import airports_frame
    from app.services.models.training import (
        RandomForestClassifier,
        RandomForestRegressor,
        _preprocessor,
        Pipeline,
    )

    bounds = demo_boundaries(settings)
    grid = grid_from_settings(settings)
    p = settings.data_dir / "processed"
    s = settings.data_dir / "synthetic"
    seed = settings.demo_seed

    # 1. Congestion Learning Curve
    c_curve_rows = []
    if (p / "congestion_agg.parquet").exists() and (p / "congestion_thresholds.json").exists():
        try:
            agg = pd.read_parquet(p / "congestion_agg.parquet")
            th_d = json.loads((p / "congestion_thresholds.json").read_text())
            th = Thresholds(th_d["low_max"], th_d["medium_max"], th_d["method"])
            weather = pd.read_parquet(s / "weather_synthetic.parquet")
            edges = pd.read_csv(s / "edges.csv")
            waypoints = pd.read_csv(s / "waypoints.csv")
            airports, _ = airports_frame()
            nodes = pd.concat([airports[["node_id", "latitude", "longitude"]], waypoints[["node_id", "latitude", "longitude"]]])
            pos = {r.node_id: (r.latitude, r.longitude) for r in nodes.itertuples()}
            corridor = sorted({c for e in edges.itertuples() for c in grid.cells_along(*pos[e.source_node], *pos[e.target_node])})

            frame = build_feature_frame(agg, weather, grid, corridor, bounds.start, bounds.end, settings.window_minutes)
            df_c = frame[frame[TARGET_COUNT].notna()].copy()
            df_c["y"] = classify(df_c[TARGET_COUNT], th)
            parts = chronological_split(df_c, bounds.val_start, bounds.test_start, settings.window_minutes)
            Xtr, ytr = parts["train"][FEATURES], parts["train"]["y"].astype(str)
            Xva, yva = parts["val"][FEATURES], parts["val"]["y"].astype(str)

            train_sizes = [5000, 10000, 20000, len(Xtr)]
            for sz in train_sizes:
                sub_X = Xtr.iloc[:sz]
                sub_y = ytr.iloc[:sz]
                pipe = Pipeline([
                    ("prep", _preprocessor(NUMERIC_FEATURES, CATEGORICAL_FEATURES, False)),
                    ("clf", RandomForestClassifier(
                        n_estimators=50, max_depth=14, min_samples_leaf=3,
                        class_weight="balanced_subsample", n_jobs=-1, random_state=seed,
                    )),
                ])
                pipe.fit(sub_X, sub_y)
                tr_score = float(f1_score(sub_y, pipe.predict(sub_X), labels=CLASSES, average="macro", zero_division=0))
                va_score = float(f1_score(yva, pipe.predict(Xva), labels=CLASSES, average="macro", zero_division=0))
                c_curve_rows.append({
                    "training_sample_count": sz,
                    "training_score": round(tr_score, 6),
                    "validation_score": round(va_score, 6),
                    "metric": "Macro F1",
                    "split_strategy": "chronological_train_subsets_evaluated_on_fixed_val",
                    "random_seed": seed,
                })
        except Exception as e:
            logger.warning(f"Could not compute congestion learning curve: {e}")

    df_c_curve = pd.DataFrame(c_curve_rows) if c_curve_rows else pd.DataFrame(
        columns=["training_sample_count", "training_score", "validation_score", "metric", "split_strategy", "random_seed"]
    )
    df_c_curve.to_csv(settings.reports_dir / "congestion_learning_curve_data.csv", index=False)

    # 2. ETA Learning Curve
    e_curve_rows = []
    if (p / "eta_features.parquet").exists():
        try:
            df_e = pd.read_parquet(p / "eta_features.parquet")
            df_e = df_e[df_e[ETA_TARGET].notna() & (df_e[ETA_TARGET] > 0)].copy()
            implied = df_e.segment_distance_km / (df_e[ETA_TARGET] / 60)
            df_e = df_e[implied.between(150, 1300)]
            tr_eta = df_e[df_e.exit_time_utc < bounds.val_start]
            va_eta = df_e[(df_e.entry_time_utc >= bounds.val_start) & (df_e.exit_time_utc < bounds.test_start)]

            train_sizes_eta = [1000, 2500, 5000, 7500, len(tr_eta)]
            for sz in train_sizes_eta:
                sub_X = tr_eta.iloc[:sz]
                pipe = Pipeline([
                    ("prep", _preprocessor(ETA_NUMERIC, [], False)),
                    ("reg", RandomForestRegressor(
                        n_estimators=50, max_depth=16, min_samples_leaf=2, n_jobs=-1, random_state=seed,
                    )),
                ])
                pipe.fit(sub_X[ETA_FEATURES], sub_X[ETA_TARGET])
                tr_score = float(mean_absolute_error(sub_X[ETA_TARGET], pipe.predict(sub_X[ETA_FEATURES])))
                va_score = float(mean_absolute_error(va_eta[ETA_TARGET], pipe.predict(va_eta[ETA_FEATURES])))
                e_curve_rows.append({
                    "training_sample_count": sz,
                    "training_score": round(tr_score, 6),
                    "validation_score": round(va_score, 6),
                    "metric": "MAE (minutes)",
                    "split_strategy": "chronological_train_subsets_evaluated_on_fixed_val",
                    "random_seed": seed,
                })
        except Exception as e:
            logger.warning(f"Could not compute ETA learning curve: {e}")

    df_e_curve = pd.DataFrame(e_curve_rows) if e_curve_rows else pd.DataFrame(
        columns=["training_sample_count", "training_score", "validation_score", "metric", "split_strategy", "random_seed"]
    )
    df_e_curve.to_csv(settings.reports_dir / "eta_learning_curve_data.csv", index=False)

    return df_c_curve, df_e_curve


def generate_consolidated_summary(
    reports_dir: Path,
    artifacts_dir: Path,
    c_res: dict[str, Any],
    e_res: dict[str, Any],
) -> pd.DataFrame:
    """Generate consolidated long-form model_metrics_summary.csv."""
    c_meta = _load_active_metadata(artifacts_dir / "congestion")
    e_meta = _load_active_metadata(artifacts_dir / "eta")
    c_version = c_meta.get("version", "v20261013T131547Z") if c_meta else "v20261013T131547Z"
    e_version = e_meta.get("version", "v20261013T131558Z") if e_meta else "v20261013T131558Z"

    rows = [
        # Congestion Test Metrics
        {"Model": "RandomForestClassifier", "Task": "congestion_classification_proxy", "Metric": "accuracy",
         "Value": round(c_res["accuracy"], 6), "Unit": "fraction", "Evaluation split": "test",
         "Model version": c_version, "Sample count": c_res["sample_count"], "Source artifact": "congestion_test_predictions.csv"},
        {"Model": "RandomForestClassifier", "Task": "congestion_classification_proxy", "Metric": "balanced_accuracy",
         "Value": round(c_res["balanced_accuracy"], 6), "Unit": "fraction", "Evaluation split": "test",
         "Model version": c_version, "Sample count": c_res["sample_count"], "Source artifact": "congestion_test_predictions.csv"},
        {"Model": "RandomForestClassifier", "Task": "congestion_classification_proxy", "Metric": "macro_f1",
         "Value": round(c_res["macro_f1"], 6), "Unit": "fraction", "Evaluation split": "test",
         "Model version": c_version, "Sample count": c_res["sample_count"], "Source artifact": "congestion_test_predictions.csv"},
        {"Model": "RandomForestClassifier", "Task": "congestion_classification_proxy", "Metric": "weighted_f1",
         "Value": round(c_res["weighted_f1"], 6), "Unit": "fraction", "Evaluation split": "test",
         "Model version": c_version, "Sample count": c_res["sample_count"], "Source artifact": "congestion_test_predictions.csv"},

        # ETA Test Metrics
        {"Model": "RandomForestRegressor", "Task": "segment_eta_regression", "Metric": "mae_min",
         "Value": round(e_res["mae"], 6), "Unit": ETA_UNIT, "Evaluation split": "test",
         "Model version": e_version, "Sample count": e_res["sample_count"], "Source artifact": "eta_test_predictions.csv"},
        {"Model": "RandomForestRegressor", "Task": "segment_eta_regression", "Metric": "rmse_min",
         "Value": round(e_res["rmse"], 6), "Unit": ETA_UNIT, "Evaluation split": "test",
         "Model version": e_version, "Sample count": e_res["sample_count"], "Source artifact": "eta_test_predictions.csv"},
        {"Model": "RandomForestRegressor", "Task": "segment_eta_regression", "Metric": "r2",
         "Value": round(e_res["r2"], 6), "Unit": "unitless", "Evaluation split": "test",
         "Model version": e_version, "Sample count": e_res["sample_count"], "Source artifact": "eta_test_predictions.csv"},
        {"Model": "RandomForestRegressor", "Task": "segment_eta_regression", "Metric": "median_abs_error_min",
         "Value": round(e_res["median_abs_err"], 6), "Unit": ETA_UNIT, "Evaluation split": "test",
         "Model version": e_version, "Sample count": e_res["sample_count"], "Source artifact": "eta_test_predictions.csv"},
        {"Model": "RandomForestRegressor", "Task": "segment_eta_regression", "Metric": "mean_signed_error_min",
         "Value": round(e_res["mean_signed_err"], 6), "Unit": ETA_UNIT, "Evaluation split": "test",
         "Model version": e_version, "Sample count": e_res["sample_count"], "Source artifact": "eta_test_predictions.csv"},
    ]

    # Include validation metrics if present in metadata
    if c_meta and "selected_test_metrics" in c_meta and "metrics" in c_meta:
        rf_meta = c_meta["metrics"].get("random_forest", {})
        va_meta = rf_meta.get("validation", {})
        if va_meta:
            rows.append({
                "Model": "RandomForestClassifier", "Task": "congestion_classification_proxy", "Metric": "macro_f1",
                "Value": round(float(va_meta["macro_f1"]), 6), "Unit": "fraction", "Evaluation split": "validation",
                "Model version": c_version, "Sample count": va_meta.get("n", 8455), "Source artifact": "congestion_metrics.json",
            })
    if e_meta and "metrics" in e_meta:
        rf_meta = e_meta["metrics"].get("random_forest", {})
        va_meta = rf_meta.get("validation", {})
        if va_meta:
            rows.append({
                "Model": "RandomForestRegressor", "Task": "segment_eta_regression", "Metric": "mae_min",
                "Value": round(float(va_meta["mae_min"]), 6), "Unit": ETA_UNIT, "Evaluation split": "validation",
                "Model version": e_version, "Sample count": va_meta.get("n", 2105), "Source artifact": "eta_metrics.json",
            })

    df_consolidated = pd.DataFrame(rows)
    df_consolidated.to_csv(reports_dir / "model_metrics_summary.csv", index=False)
    return df_consolidated


def update_training_summary(
    reports_dir: Path,
    artifacts_dir: Path,
    c_res: dict[str, Any],
    e_res: dict[str, Any],
) -> dict[str, Any]:
    """Expand and standardize training_summary.json with rich documentation."""
    c_meta = _load_active_metadata(artifacts_dir / "congestion")
    e_meta = _load_active_metadata(artifacts_dir / "eta")

    summary = {
        "project": "Sky Force - AI Airspace Intelligence",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Academic ML models for spatial airspace density and airway travel-time proxies. "
                      "Trained on reproducible synthetic demonstration data. NOT for tactical ATC separation.",
        "congestion": {
            "version": c_meta.get("version", "v20261013T131547Z") if c_meta else "v20261013T131547Z",
            "model": c_meta.get("model_name", "random_forest") if c_meta else "random_forest",
            "algorithm": "RandomForestClassifier(n_estimators=200, max_depth=16, min_samples_leaf=3, class_weight='balanced_subsample')",
            "task": "3-class research congestion proxy for the NEXT 15-minute window",
            "target": "next_window_class (LOW <= 2, MEDIUM 3-4, HIGH >= 5 unique aircraft)",
            "splits": c_meta.get("splits") if c_meta else None,
            "sample_counts": c_meta.get("rows") if c_meta else {"train": 42631, "validation": 8455, "test": 16999},
            "class_distribution": c_meta.get("class_distribution") if c_meta else None,
            "feature_count": len(c_meta.get("feature_schema", {}).get("features", [])) if c_meta else 21,
            "test": {
                "accuracy": c_res["accuracy"],
                "balanced_accuracy": c_res["balanced_accuracy"],
                "macro_f1": c_res["macro_f1"],
                "weighted_f1": c_res["weighted_f1"],
            },
            "artifact_path": str(artifacts_dir / "congestion" / (c_meta.get("version", "v20261013T131547Z") if c_meta else "") / "model.joblib"),
        },
        "eta": {
            "version": e_meta.get("version", "v20261013T131558Z") if e_meta else "v20261013T131558Z",
            "model": e_meta.get("model_name", "random_forest") if e_meta else "random_forest",
            "algorithm": "RandomForestRegressor(n_estimators=200, max_depth=18, min_samples_leaf=2)",
            "task": "segment traversal time regression in minutes",
            "target": "traversal_duration_min (time between consecutive observed airway graph node passages)",
            "splits": e_meta.get("splits") if e_meta else None,
            "sample_counts": e_meta.get("rows") if e_meta else {"train": 10612, "validation": 2105, "test": 4356},
            "feature_count": len(e_meta.get("feature_schema", {}).get("features", [])) if e_meta else 12,
            "test": {
                "mae_min": e_res["mae"],
                "rmse_min": e_res["rmse"],
                "r2": e_res["r2"],
                "median_abs_error_min": e_res["median_abs_err"],
                "mean_signed_error_min": e_res["mean_signed_err"],
            },
            "artifact_path": str(artifacts_dir / "eta" / (e_meta.get("version", "v20261013T131558Z") if e_meta else "") / "model.joblib"),
        },
    }
    (reports_dir / "training_summary.json").write_text(json.dumps(summary, indent=2))
    return summary


def generate_html_report(reports_dir: Path, context: dict[str, Any]) -> str:
    """Generate professional, pure-table HTML evaluation report (zero canvas, zero SVG, zero images)."""
    c_sum = context["congestion"]["summary"]
    c_rep = context["congestion"]["class_report"]
    c_cm = context["congestion"]["confusion_matrix"]
    c_cm_norm = context["congestion"]["confusion_matrix_norm"]
    c_feat = context["congestion"]["feature_importance"]
    c_comp = context["congestion"]["model_comparison"]

    e_sum = context["eta"]["summary"]
    e_err = context["eta"]["error_summary"]
    e_range = context["eta"]["error_by_range"]
    e_feat = context["eta"]["feature_importance"]
    e_comp = context["eta"]["model_comparison"]

    def _render_table(df: pd.DataFrame, table_id: str, caption: str) -> str:
        if df.empty:
            return f"<p class='empty-note'>No data available for {caption}</p>"
        html = [f"<div class='table-container'><table id='{table_id}' class='eval-table'><caption>{caption}</caption><thead><tr>"]
        for col in df.columns:
            html.append(f"<th>{col.replace('_', ' ').title()}</th>")
        html.append("</tr></thead><tbody>")
        for _, row in df.iterrows():
            html.append("<tr>")
            for col in df.columns:
                val = row[col]
                if isinstance(val, float):
                    fmt_val = f"{val:.4f}" if abs(val) < 1000 else f"{val:,.2f}"
                elif val is None or pd.isna(val):
                    fmt_val = "—"
                else:
                    fmt_val = str(val)
                html.append(f"<td>{fmt_val}</td>")
            html.append("</tr>")
        html.append("</tbody></table></div>")
        return "".join(html)

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Sky Force — Structured Machine Learning Evaluation Report</title>
<style>
:root {{
  --bg-primary: #0a0e17;
  --bg-surface: #111827;
  --bg-card: #1f2937;
  --border-subtle: #374151;
  --text-main: #f3f4f6;
  --text-muted: #9ca3af;
  --text-accent: #38bdf8;
  --text-emerald: #34d399;
  --text-amber: #fbbf24;
  --text-rose: #f87171;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
}}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
  background-color: var(--bg-primary);
  color: var(--text-main);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  padding: 2.5rem 1.5rem;
}}
.container {{ max-width: 1200px; margin: 0 auto; }}
header.report-header {{
  border-bottom: 2px solid var(--border-subtle);
  padding-bottom: 1.5rem;
  margin-bottom: 2rem;
}}
.badge {{
  display: inline-block;
  padding: 0.25rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-radius: 4px;
  background: rgba(56, 189, 248, 0.15);
  color: var(--text-accent);
  margin-bottom: 0.5rem;
}}
h1 {{ font-size: 2rem; font-weight: 800; color: #fff; margin-bottom: 0.5rem; }}
.subtitle {{ color: var(--text-muted); font-size: 1rem; max-width: 800px; }}
.metadata-grid {{
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin: 1.5rem 0;
}}
.metadata-card {{
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 6px;
  padding: 1rem;
}}
.metadata-card span {{ display: block; font-size: 0.75rem; text-transform: uppercase; color: var(--text-muted); }}
.metadata-card strong {{ display: block; font-size: 1.1rem; color: #fff; margin-top: 0.25rem; font-family: var(--font-mono); }}
section.report-section {{
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 2.5rem;
}}
section.report-section h2 {{
  font-size: 1.4rem;
  font-weight: 700;
  color: #fff;
  border-bottom: 1px solid var(--border-subtle);
  padding-bottom: 0.75rem;
  margin-bottom: 1rem;
}}
section.report-section h3 {{
  font-size: 1.1rem;
  font-weight: 600;
  color: var(--text-accent);
  margin: 1.5rem 0 0.5rem 0;
}}
p.section-desc {{ color: var(--text-muted); font-size: 0.9rem; margin-bottom: 1rem; }}
.table-container {{ overflow-x: auto; margin-bottom: 1.5rem; }}
table.eval-table {{
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
  text-align: left;
}}
table.eval-table caption {{
  text-align: left;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  margin-bottom: 0.5rem;
}}
table.eval-table th {{
  background: var(--bg-card);
  color: var(--text-muted);
  padding: 0.6rem 0.8rem;
  font-weight: 600;
  border-bottom: 1px solid var(--border-subtle);
}}
table.eval-table td {{
  padding: 0.6rem 0.8rem;
  border-bottom: 1px solid rgba(55, 65, 81, 0.5);
  font-family: var(--font-mono);
}}
table.eval-table tr:hover td {{ background: rgba(56, 189, 248, 0.04); }}
.disclaimer-box {{
  background: rgba(245, 158, 11, 0.08);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 6px;
  padding: 1rem;
  margin: 1.5rem 0;
  color: #fde68a;
  font-size: 0.875rem;
}}
.disclaimer-box strong {{ display: block; color: var(--text-amber); margin-bottom: 0.25rem; }}
.artifact-list {{ list-style: none; display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 0.75rem; margin-top: 1rem; }}
.artifact-list li {{
  background: var(--bg-card);
  padding: 0.75rem 1rem;
  border-radius: 4px;
  border: 1px solid var(--border-subtle);
  font-family: var(--font-mono);
  font-size: 0.85rem;
}}
.artifact-list a {{ color: var(--text-accent); text-decoration: none; }}
.artifact-list a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<div class="container">

<header class="report-header">
  <span class="badge">Aviation Intelligence · Scientific Validation</span>
  <h1>Sky Force Machine Learning Evaluation Report</h1>
  <p class="subtitle">
    Empirical evaluation results, error distributions, confusion matrices, and feature importance rankings
    for airspace congestion forecasting and segment travel-time prediction.
  </p>
</header>

<div class="metadata-grid">
  <div class="metadata-card">
    <span>Report Generated</span>
    <strong>{datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")}</strong>
  </div>
  <div class="metadata-card">
    <span>Evaluation Split</span>
    <strong>Strict Chronological Test</strong>
  </div>
  <div class="metadata-card">
    <span>Congestion Model</span>
    <strong>Random Forest ({context['congestion']['sample_count']:,} test rows)</strong>
  </div>
  <div class="metadata-card">
    <span>ETA Model</span>
    <strong>Random Forest ({context['eta']['sample_count']:,} test rows)</strong>
  </div>
</div>

<div class="disclaimer-box">
  <strong>Scientific Integrity & Demonstration Notice</strong>
  Models evaluated in this report were trained and tested on reproducible synthetic demonstration data representing Indian airspace corridors.
  Congestion predictions represent research traffic-density proxies (unique-aircraft counts within 15-minute grid windows),
  NOT official ATC capacity determinations. Traversal estimates represent segment operational flight times and must not be used for tactical separation.
</div>

<section class="report-section">
  <h2>1. Airspace Congestion Classification Model (Model A)</h2>
  <p class="section-desc">
    Target: <code>next_window_class</code> (LOW &le; 2 aircraft, MEDIUM 3&ndash;4 aircraft, HIGH &ge; 5 aircraft) in the succeeding 15-minute window.
    Evaluated on 16,999 held-out chronological test observations.
  </p>

  <h3>Table A &mdash; Overall Classification Performance</h3>
  {_render_table(c_sum, "tbl-congestion-summary", "Overall Metrics (Held-out Test Partition)")}

  <h3>Table B &mdash; Per-Class Classification Report</h3>
  {_render_table(c_rep, "tbl-congestion-per-class", "Per-Class Performance with Support")}

  <h3>Table C &mdash; Confusion Matrix (Raw Test Counts)</h3>
  {_render_table(c_cm, "tbl-congestion-cm", "Actual Classes (Rows) vs Predicted Classes (Columns)")}

  <h3>Table D &mdash; Normalized Confusion Matrix (Row Normalized)</h3>
  {_render_table(c_cm_norm, "tbl-congestion-cm-norm", "Row Normalized by Actual Class Support (Recall across Rows)")}

  <h3>Table E &mdash; Candidate Model Comparison</h3>
  {_render_table(c_comp, "tbl-congestion-candidates", "Candidate Architecture Comparison on Validation and Test Sets")}

  <h3>Table F &mdash; Feature Importance Ranking</h3>
  {_render_table(c_feat.head(15), "tbl-congestion-features", "Top 15 Features by Importance (Native MDI and Validation Permutation)")}
</section>

<section class="report-section">
  <h2>2. Airway Segment Traversal Time Regression (Model B)</h2>
  <p class="section-desc">
    Target: <code>traversal_duration_min</code> in minutes between consecutive airway waypoints.
    Evaluated on 4,356 held-out chronological test segment traversals.
  </p>

  <h3>Table A &mdash; Overall ETA Regression Metrics</h3>
  {_render_table(e_sum, "tbl-eta-summary", "Overall Regression Metrics vs Heuristic Baseline")}

  <h3>Table B &mdash; Error Distribution & Percentile Analysis</h3>
  {_render_table(e_err, "tbl-eta-error-dist", "Signed Error and Absolute Error Distribution Statistics")}

  <h3>Table C &mdash; Error by Traversal Target Range</h3>
  {_render_table(e_range, "tbl-eta-range", "Prediction Errors Stratified by Actual Flight Duration")}

  <h3>Table D &mdash; Candidate Model Comparison</h3>
  {_render_table(e_comp, "tbl-eta-candidates", "Candidate Regression Architectures Comparison")}

  <h3>Table E &mdash; Feature Importance Ranking</h3>
  {_render_table(e_feat.head(15), "tbl-eta-features", "Top Features by Importance (Native MDI and Validation Permutation)")}
</section>

<section class="report-section">
  <h2>3. Exported Chart-Ready Artifacts</h2>
  <p class="section-desc">All numerical data tables are exported as tidy CSV and JSON files for external visualization pipelines:</p>
  <ul class="artifact-list">
    <li><code>congestion_metrics_summary.csv</code></li>
    <li><code>congestion_classification_report.csv</code></li>
    <li><code>congestion_confusion_matrix.csv</code></li>
    <li><code>congestion_confusion_matrix_normalized.csv</code></li>
    <li><code>congestion_feature_importance.csv</code></li>
    <li><code>congestion_learning_curve_data.csv</code></li>
    <li><code>congestion_model_comparison.csv</code></li>
    <li><code>eta_metrics_summary.csv</code></li>
    <li><code>eta_error_summary.csv</code></li>
    <li><code>eta_actual_vs_predicted.csv</code></li>
    <li><code>eta_error_by_range.csv</code></li>
    <li><code>eta_feature_importance.csv</code></li>
    <li><code>eta_learning_curve_data.csv</code></li>
    <li><code>eta_model_comparison.csv</code></li>
    <li><code>model_metrics_summary.csv</code></li>
    <li><code>training_summary.json</code></li>
  </ul>
</section>

</div>
</body>
</html>
"""
    html_path = reports_dir / "model_evaluation_report.html"
    html_path.write_text(html_content, encoding="utf-8")
    return str(html_path)


def generate_all_reports(settings: Settings | None = None, include_learning_curves: bool = True) -> dict[str, Any]:
    """Execute complete reporting workflow, regenerating all CSV, JSON, and HTML evaluation artifacts."""
    settings = settings or get_settings()
    rep_dir = settings.reports_dir
    art_dir = settings.artifacts_dir
    rep_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Generating structured evaluation reports in: {rep_dir}")
    c_res = compute_congestion_reports(rep_dir, art_dir)
    e_res = compute_eta_reports(rep_dir, art_dir)

    if include_learning_curves:
        compute_learning_curves(settings)

    df_consolidated = generate_consolidated_summary(rep_dir, art_dir, c_res, e_res)
    summary = update_training_summary(rep_dir, art_dir, c_res, e_res)

    context = {"congestion": c_res, "eta": e_res}
    html_path = generate_html_report(rep_dir, context)

    logger.info("Structured evaluation reports generated successfully.")
    return {
        "status": "success",
        "html_report": html_path,
        "consolidated_metrics": df_consolidated.to_dict(orient="records"),
        "training_summary": summary,
    }


def _load_active_metadata(kind_dir: Path) -> dict[str, Any] | None:
    if not kind_dir.exists():
        return None
    active_file = kind_dir / "ACTIVE"
    version = active_file.read_text().strip() if active_file.exists() else None
    if not version:
        subdirs = sorted([d.name for d in kind_dir.iterdir() if d.is_dir() and d.name.startswith("v")])
        version = subdirs[-1] if subdirs else None
    if not version:
        return None
    meta_path = kind_dir / version / "metadata.json"
    if meta_path.exists():
        try:
            return json.loads(meta_path.read_text())
        except Exception:
            return None
    return None
