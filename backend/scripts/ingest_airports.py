"""Download the OurAirports reference subset used by the demo network.

Usage:  python scripts/ingest_airports.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ingestion.ourairports import fetch_and_store_subset  # noqa: E402

if __name__ == "__main__":
    meta = fetch_and_store_subset()
    print(json.dumps(meta, indent=2))
