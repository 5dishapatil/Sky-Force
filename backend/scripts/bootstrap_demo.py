"""Initialise the database and the deterministic SYNTHETIC demo dataset.

Usage (from backend/):  python scripts/bootstrap_demo.py [--train]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.services.ingestion.bootstrap import run_bootstrap  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--train", action="store_true", help="also train the models after bootstrapping")
    args = ap.parse_args()
    configure_logging("INFO")
    s = get_settings()
    print(json.dumps(run_bootstrap(s), indent=2, default=str))
    if args.train:
        from app.services.models.pipeline import run_training

        print(json.dumps(run_training(s), indent=2, default=str))
