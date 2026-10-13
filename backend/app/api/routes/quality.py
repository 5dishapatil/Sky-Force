"""Data quality audit summary endpoints."""
from __future__ import annotations

import json
from pathlib import Path
from fastapi import APIRouter

from app.api.state import get_state
from app.schemas.common import DataQualitySummaryResponse

router = APIRouter(prefix="/data-quality", tags=["Data Quality"])


@router.get("/summary", response_model=DataQualitySummaryResponse)
def get_data_quality_summary() -> DataQualitySummaryResponse:
    state = get_state()
    p = state.settings.data_dir / "processed" / "data_quality_report.json"
    if p.exists():
        data = json.loads(p.read_text())
        return DataQualitySummaryResponse(
            dataset=data.get("dataset", state.settings.demo_dataset_id),
            input_rows=data.get("input_rows", 0),
            retained_rows=data.get("retained_rows", 0),
            dropped=data.get("dropped", {}),
            flagged=data.get("flagged", {}),
            missing_profile_pct=data.get("missing_profile_pct", {}),
            time_range_utc=data.get("time_range_utc", [None, None]),
            inferred_tracks=data.get("inferred_tracks", 0),
            generated_at_utc=data.get("generated_at_utc", ""),
        )
    return DataQualitySummaryResponse(
        dataset=state.settings.demo_dataset_id,
        input_rows=0,
        retained_rows=0,
        dropped={},
        flagged={},
        missing_profile_pct={},
        time_range_utc=[None, None],
        inferred_tracks=0,
        generated_at_utc="",
    )
