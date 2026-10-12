"""OurAirports reference-data adapter.

OurAirports data (https://ourairports.com/data/) is released into the public
domain. We download ``airports.csv`` once, filter a small set of ICAO codes
for the demonstration region, and store the subset with retrieval metadata in
``data/reference/airports_subset.csv`` so later runs work offline.
"""
from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from app.core.config import get_settings
from app.services.ingestion.http import request_with_retry

# Demonstration airport set (Indian subcontinent). Coordinates are NOT typed
# in by hand: they are read from OurAirports (or the cached subset).
DEMO_ICAO = [
    "VIDP", "VABB", "VOBL", "VOMM", "VOHS", "VECC", "VAAH", "VAPO", "VOGO", "VIJP",
    "VILK", "VANP", "VABP", "VOCI", "VEBS", "VAID", "VIAR", "VEGT", "VOTV",
]

SUBSET_COLUMNS = [
    "ident", "type", "name", "latitude_deg", "longitude_deg", "elevation_ft",
    "iso_country", "municipality", "gps_code", "iata_code",
]


def subset_paths() -> tuple[Path, Path]:
    ref = get_settings().data_dir / "reference"
    return ref / "airports_subset.csv", ref / "airports_subset.meta.json"


def fetch_and_store_subset(icao_codes: list[str] | None = None) -> dict:
    s = get_settings()
    codes = icao_codes or DEMO_ICAO
    resp = request_with_retry("GET", s.ourairports_csv_url, timeout=60, source_name="OurAirports")
    resp.raise_for_status()
    raw = resp.content
    df = pd.read_csv(io.BytesIO(raw), low_memory=False)
    sub = df[df["ident"].isin(codes)][SUBSET_COLUMNS].copy()
    csv_path, meta_path = subset_paths()
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    sub.to_csv(csv_path, index=False)
    meta = {
        "source": "OurAirports",
        "url": s.ourairports_csv_url,
        "licence": "Public domain (OurAirports data dedication)",
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "full_file_sha256": hashlib.sha256(raw).hexdigest(),
        "full_file_rows": int(len(df)),
        "subset_rows": int(len(sub)),
        "requested_icao": codes,
        "missing_icao": sorted(set(codes) - set(sub["ident"])),
    }
    meta_path.write_text(json.dumps(meta, indent=2))
    return meta


def load_subset() -> tuple[pd.DataFrame, dict]:
    csv_path, meta_path = subset_paths()
    if not csv_path.exists():
        raise FileNotFoundError(
            f"{csv_path} not found. Run `python scripts/ingest_airports.py` (requires Internet once)."
        )
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"source": "unknown"}
    return pd.read_csv(csv_path), meta
