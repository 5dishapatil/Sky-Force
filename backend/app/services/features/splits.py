"""Chronological partition boundaries - defined in ONE place.

For the 8-day demo dataset (2026-01-15 .. 2026-01-22 UTC):
  train      : 2026-01-15 00:00 -> 2026-01-20 00:00   (5 days)
  validation : 2026-01-20 00:00 -> 2026-01-21 00:00   (1 day)
  test       : 2026-01-21 00:00 -> 2026-01-23 00:00   (2 days)
"""
from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class SplitBoundaries:
    start: pd.Timestamp
    val_start: pd.Timestamp
    test_start: pd.Timestamp
    end: pd.Timestamp

    def to_dict(self) -> dict:
        return {
            "train": [self.start.isoformat(), self.val_start.isoformat()],
            "validation": [self.val_start.isoformat(), self.test_start.isoformat()],
            "test": [self.test_start.isoformat(), self.end.isoformat()],
            "method": "chronological; rows whose target window crosses a boundary are purged",
        }

    def partition_of(self, ts: pd.Timestamp) -> str:
        if ts < self.val_start:
            return "train"
        if ts < self.test_start:
            return "validation"
        return "test"


def demo_boundaries(settings, val_days: int = 1, test_days: int = 2) -> SplitBoundaries:  # noqa: ANN001
    start = pd.Timestamp(settings.demo_start_utc)
    end = start + pd.Timedelta(days=settings.demo_days)
    test_start = end - pd.Timedelta(days=test_days)
    val_start = test_start - pd.Timedelta(days=val_days)
    return SplitBoundaries(start, val_start, test_start, end)
