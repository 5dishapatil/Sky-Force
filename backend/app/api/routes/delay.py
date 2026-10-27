"""FastAPI route handlers for Flight Delay Prediction & Passenger-Centred Intelligence."""
from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.delay import (
    AlternativeFlightsResponse,
    DataReadinessReport,
    DelayDashboardResponse,
    DelayPredictionRequest,
    FlightDetail,
    FlightSearchResponse,
    OperationalStage,
)
from app.services.delay.service import FlightDelayService

router = APIRouter(prefix="/delay", tags=["Flight Delay Intelligence"])
_service = FlightDelayService()


@router.get("/flights", response_model=FlightSearchResponse)
def search_flights(
    query: Annotated[str | None, Query(description="Search by flight number, callsign, or airport code")] = None,
    date: Annotated[str | None, Query(description="Date filter in YYYY-MM-DD format")] = None,
    origin: Annotated[str | None, Query(description="Origin airport IATA or node ID")] = None,
    destination: Annotated[str | None, Query(description="Destination airport IATA or node ID")] = None,
    limit: Annotated[int, Query(ge=1, le=100, description="Page limit")] = 25,
    offset: Annotated[int, Query(ge=0, description="Page offset")] = 0,
) -> FlightSearchResponse:
    """Search available flights across the surveillance repository."""
    return _service.search_flights(
        query=query,
        date_str=date,
        origin=origin,
        destination=destination,
        limit=limit,
        offset=offset,
    )


@router.get("/flights/{flight_id}", response_model=FlightDetail)
def get_flight_detail(flight_id: str) -> FlightDetail:
    """Retrieve complete flight departure status, delay estimate, and contributing factors."""
    detail = _service.get_flight_detail(flight_id)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight '{flight_id}' not found in the surveillance database.",
        )
    return detail


@router.get("/flights/{flight_id}/timeline", response_model=list[OperationalStage])
def get_flight_timeline(flight_id: str) -> list[OperationalStage]:
    """Retrieve 8-stage operational departure progress timeline for the flight."""
    timeline = _service.get_timeline(flight_id)
    if timeline is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight '{flight_id}' not found in the surveillance database.",
        )
    return timeline


@router.get("/flights/{flight_id}/alternatives", response_model=AlternativeFlightsResponse)
def get_alternative_flights(flight_id: str) -> AlternativeFlightsResponse:
    """Retrieve viable alternative flights on the same origin-destination city pair."""
    alts = _service.get_alternatives(flight_id)
    if alts is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight '{flight_id}' not found in the surveillance database.",
        )
    return alts


@router.post("/predict", response_model=FlightDetail)
def predict_scenario_delay(request: DelayPredictionRequest) -> FlightDetail:
    """Dynamically recalculate departure delay and timeline under hypothetical scenario conditions."""
    detail = _service.predict_scenario(request)
    if not detail:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Flight '{request.flight_id}' not found.",
        )
    return detail


@router.get("/dashboard", response_model=DelayDashboardResponse)
def get_delay_dashboard(
    sample_size: Annotated[int, Query(ge=20, le=500, description="Sample size for dashboard")] = 150,
) -> DelayDashboardResponse:
    """Retrieve high-level delay risks, attention flights, and factor breakdowns for Operations Console."""
    return _service.get_dashboard(sample_size=sample_size)


@router.get("/readiness", response_model=DataReadinessReport)
def get_data_readiness_report() -> DataReadinessReport:
    """Retrieve transparent gap analysis explaining current demonstration state vs production ML requirements."""
    return _service.get_readiness_report()

