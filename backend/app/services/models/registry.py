"""Versioned model-artifact registry.

Layout::

    ml/artifacts/<kind>/<version>/model.joblib
    ml/artifacts/<kind>/<version>/metadata.json   (includes sha256 of model.joblib)
    ml/artifacts/<kind>/ACTIVE                    (text file: active version)

Safety: joblib uses pickle, which can execute code. We therefore ONLY load
files located inside the project's artifacts directory, and only after the
SHA-256 checksum matches the value recorded at training time. Never point
this loader at untrusted files.
"""
from __future__ import annotations

import hashlib
import json
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.core.errors import ModelUnavailableError, ValidationFailed


@dataclass
class LoadedModel:
    kind: str
    version: str
    pipeline: Any
    metadata: dict[str, Any]

    @property
    def features(self) -> list[str]:
        return list(self.metadata["feature_schema"]["features"])


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def library_versions() -> dict[str, str]:
    import networkx
    import sklearn

    return {"python": platform.python_version(), "scikit-learn": sklearn.__version__, "pandas": pd.__version__,
            "numpy": np.__version__, "joblib": joblib.__version__, "networkx": networkx.__version__}


def save_artifact(kind: str, pipeline: Any, metadata: dict[str, Any], artifacts_dir: Path | None = None) -> tuple[str, Path]:
    root = (artifacts_dir or get_settings().artifacts_dir) / kind
    version = datetime.now(timezone.utc).strftime("v%Y%m%dT%H%M%SZ")
    d = root / version
    d.mkdir(parents=True, exist_ok=True)
    model_path = d / "model.joblib"
    joblib.dump(pipeline, model_path)
    metadata = {**metadata, "kind": kind, "version": version, "sha256": _sha256(model_path),
                "library_versions": library_versions()}
    (d / "metadata.json").write_text(json.dumps(metadata, indent=2, default=str))
    (root / "ACTIVE").write_text(version)
    return version, d


def active_version(kind: str, artifacts_dir: Path | None = None) -> str | None:
    p = (artifacts_dir or get_settings().artifacts_dir) / kind / "ACTIVE"
    return p.read_text().strip() if p.exists() else None


def read_metadata(kind: str, version: str | None = None, artifacts_dir: Path | None = None) -> dict[str, Any] | None:
    root = (artifacts_dir or get_settings().artifacts_dir) / kind
    version = version or active_version(kind, artifacts_dir)
    if not version:
        return None
    p = root / version / "metadata.json"
    return json.loads(p.read_text()) if p.exists() else None


def load_active(kind: str, artifacts_dir: Path | None = None) -> LoadedModel:
    root = (artifacts_dir or get_settings().artifacts_dir).resolve()
    version = active_version(kind, root)
    if not version:
        raise ModelUnavailableError(f"No trained '{kind}' model found. Run `python scripts/train_models.py`.",
                                    details={"kind": kind})
    d = (root / kind / version).resolve()
    if root not in d.parents:
        raise ModelUnavailableError("Artifact path outside the artifacts directory was rejected.")
    meta_path, model_path = d / "metadata.json", d / "model.joblib"
    if not (meta_path.exists() and model_path.exists()):
        raise ModelUnavailableError(f"Artifact files for {kind}/{version} are missing.")
    meta = json.loads(meta_path.read_text())
    if _sha256(model_path) != meta.get("sha256"):
        raise ModelUnavailableError(f"Checksum mismatch for {kind}/{version}; refusing to load.")
    return LoadedModel(kind, version, joblib.load(model_path), meta)


def validate_features(df: pd.DataFrame, model: LoadedModel) -> tuple[pd.DataFrame, list[str]]:
    """Return the frame restricted/ordered to the model schema plus warnings.
    Missing required columns -> ValidationFailed. Extra columns are ignored but reported."""
    schema = model.metadata["feature_schema"]
    feats = schema["features"]
    missing = [c for c in feats if c not in df.columns]
    if missing:
        raise ValidationFailed("Input is missing model features", details={"missing": missing})
    warnings = []
    extra = sorted(set(df.columns) - set(feats) - set(schema.get("allowed_extra", [])))
    if extra:
        warnings.append(f"Ignored unexpected columns: {extra[:8]}")
    out = df[feats].copy()
    for c in schema.get("numeric", []):
        out[c] = pd.to_numeric(out[c], errors="coerce")
    for c in schema.get("categorical", []):
        out[c] = out[c].astype(str)
        known = set(schema.get("categories", {}).get(c, []))
        unknown = sorted(set(out[c]) - known) if known else []
        if unknown:
            warnings.append(f"Unseen categories for {c}: {unknown[:5]} (encoded as all-zero)")
    return out, warnings


def ood_flags(row: pd.Series, model: LoadedModel) -> list[str]:
    """Features outside the [p1, p99] range observed in training."""
    rng = model.metadata.get("training_ranges", {})
    flags = []
    for f, (lo, hi) in rng.items():
        v = row.get(f)
        if v is not None and not pd.isna(v) and (v < lo or v > hi):
            flags.append(f"{f}={float(v):.2f} outside training range [{lo:.2f}, {hi:.2f}]")
    return flags
