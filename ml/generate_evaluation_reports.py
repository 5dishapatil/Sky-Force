"""Generate structured ML evaluation reports, tabular metrics, and chart-ready data files.

Usage:
    python ml/generate_evaluation_reports.py [--skip-learning-curves]

Exports all tabular evaluations, CSV artifacts, consolidated summaries,
and model_evaluation_report.html into ml/reports/ without retraining the models.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1] / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.services.models.reporting import generate_all_reports

logger = get_logger(__name__)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-learning-curves",
        action="store_true",
        help="Skip recalculating the empirical learning-curve cross-validation data",
    )
    args = parser.parse_args()

    configure_logging("INFO")
    settings = get_settings()

    print("\n" + "=" * 70)
    print("Sky Force — Structured ML Evaluation Reports Generator")
    print("=" * 70)
    print(f"Reports Directory:   {settings.reports_dir}")
    print(f"Artifacts Directory: {settings.artifacts_dir}")
    print(f"Compute Learning Curves: {not args.skip_learning_curves}")
    print("-" * 70)

    result = generate_all_reports(settings, include_learning_curves=not args.skip_learning_curves)

    print("\nGeneration completed successfully.")
    print(f"HTML Report: {result['html_report']}")
    print("Exported files in ml/reports/:")
    for p in sorted(settings.reports_dir.glob("*")):
        if p.is_file():
            print(f"  - {p.name:<45} ({p.stat().st_size:,} bytes)")
    print("=" * 70 + "\n")
