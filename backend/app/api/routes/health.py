"""Health, metadata, and data sources status endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.state import get_state
from app.core.config import DISCLAIMER
from app.db import models as m
from app.db.session import get_db
from app.schemas.common import DataSourceStatusItem, HealthResponse, MetaResponse

router = APIRouter(tags=["Health & Metadata"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    state = get_state()
    return HealthResponse(
        status="ok",
        app_name=state.settings.app_name,
        environment=state.settings.environment,
        database="sqlite" if state.settings.database_url.startswith("sqlite") else "postgresql",
        timestamp_utc=datetime.now(timezone.utc),
        disclaimer=DISCLAIMER,
    )


@router.get("/meta", response_model=MetaResponse)
def get_meta() -> MetaResponse:
    state = get_state()
    lo, hi = state.store.coverage
    return MetaResponse(
        app_name=state.settings.app_name,
        version="0.1.0",
        disclaimer=DISCLAIMER,
        research_questions=[
            "Can aircraft observations be transformed into spatial-temporal traffic density indicators?",
            "Can ML models forecast congestion and segment ETA without target leakage?",
            "Does multi-factor routing outperform distance-only baselines under airspace disruption?",
            "Can candidate route trade-offs be transparently explained with factor contributions?",
            "How does dynamic rerouting respond to simulated corridor closures and weather events?",
        ],
        active_dataset=state.settings.demo_dataset_id,
        active_models={
            "congestion": state.congestion_model.version if state.congestion_model else None,
            "eta": state.eta_model.version if state.eta_model else None,
        },
        coverage_utc=[
            lo.to_pydatetime() if lo is not None else None,
            hi.to_pydatetime() if hi is not None else None,
        ],
    )


@router.get("/data-sources/status", response_model=list[DataSourceStatusItem])
def get_data_sources_status(db: Session = Depends(get_db)) -> list[DataSourceStatusItem]:
    snapshots = db.scalars(
        select(m.DataSourceSnapshot).order_by(m.DataSourceSnapshot.retrieved_at.desc())
    ).all()
    
    seen = set()
    items = []
    for s in snapshots:
        if s.source_key not in seen:
            seen.add(s.source_key)
            items.append(
                DataSourceStatusItem(
                    source_key=s.source_key,
                    status=s.status,
                    retrieved_at_utc=s.retrieved_at,
                    record_count=s.record_count,
                    message=s.message,
                    details=s.details,
                )
            )
    return items
