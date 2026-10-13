"""Source manifest (data/source_manifest.json): provenance for every dataset used."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import get_settings


def manifest_path() -> Path:
    return get_settings().data_dir / "source_manifest.json"


def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_manifest() -> dict[str, Any]:
    p = manifest_path()
    if p.exists():
        return json.loads(p.read_text())
    return {"generated_by": "Sky Force", "entries": {}}


def upsert_entry(key: str, entry: dict[str, Any]) -> dict[str, Any]:
    m = load_manifest()
    entry = {**entry, "manifest_updated_at_utc": datetime.now(timezone.utc).isoformat()}
    m.setdefault("entries", {})[key] = entry
    p = manifest_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(m, indent=2, default=str))
    return entry
