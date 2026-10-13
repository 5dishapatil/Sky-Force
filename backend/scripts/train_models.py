"""Train and evaluate the congestion classifier and segment-ETA regressor.

Usage (from backend/):  python scripts/train_models.py [--only congestion|eta]
Requires: python scripts/bootstrap_demo.py (or prepare_dataset.py) to have run.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import get_settings  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.services.models.pipeline import run_training  # noqa: E402

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--only", choices=["congestion", "eta"])
    args = ap.parse_args()
    configure_logging("INFO")
    which = (args.only,) if args.only else ("congestion", "eta")
    print(json.dumps(run_training(get_settings(), which), indent=2, default=str))
