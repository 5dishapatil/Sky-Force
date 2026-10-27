"""Unit and integration tests for Flight Delay Prediction & Intelligence endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_delay_flights_search_and_pagination(client: TestClient) -> None:
    res = client.get("/api/delay/flights?limit=10&offset=0")
    assert res.status_code == 200
    data = res.json()
    assert "total" in data
    assert data["total"] > 0
    assert len(data["flights"]) <= 10

    first = data["flights"][0]
    assert "flight_id" in first
    assert "flight_number" in first
    assert "origin_iata" in first
    assert "destination_iata" in first
    assert "predicted_delay_minutes" in first
    assert first["status"] in ("ON_SCHEDULE", "DELAY_LIKELY", "SIGNIFICANT_DELAY_LIKELY", "DEPARTURE_UNCERTAIN")
    assert first["is_demonstration"] is True


def test_delay_flights_filter_by_query_and_airports(client: TestClient) -> None:
    # Search by DEL (Indira Gandhi)
    res = client.get("/api/delay/flights?query=DEL&limit=5")
    assert res.status_code == 200
    data = res.json()
    for f in data["flights"]:
        assert "DEL" in (f["origin_iata"], f["destination_iata"]) or "DEL" in f["flight_number"]


def test_delay_flight_detail_and_8_stage_timeline(client: TestClient) -> None:
    # First get a valid flight ID
    list_res = client.get("/api/delay/flights?limit=1")
    assert list_res.status_code == 200
    fid = list_res.json()["flights"][0]["flight_id"]

    # Fetch detail
    res = client.get(f"/api/delay/flights/{fid}")
    assert res.status_code == 200
    detail = res.json()
    assert detail["flight_id"] == fid

    # Verify distinguished gate departure vs takeoff
    assert "estimated_gate_departure_utc" in detail
    assert "estimated_takeoff_utc" in detail
    assert detail["estimated_takeoff_utc"] >= detail["estimated_gate_departure_utc"]
    assert detail["taxi_time_minutes"] > 0

    # Verify 8-stage timeline
    timeline = detail["timeline"]
    assert len(timeline) == 8
    stage_numbers = [s["stage_number"] for s in timeline]
    assert stage_numbers == [1, 2, 3, 4, 5, 6, 7, 8]

    # Verify factors with strict evidence status
    factors = detail["factors"]
    assert len(factors) >= 2
    for fact in factors:
        assert fact["evidence_status"] in ("CONFIRMED", "MODEL_INFERRED", "UNAVAILABLE", "NOT_APPLICABLE")

    # Fetch timeline standalone endpoint
    t_res = client.get(f"/api/delay/flights/{fid}/timeline")
    assert t_res.status_code == 200
    assert len(t_res.json()) == 8


def test_delay_flight_alternatives(client: TestClient) -> None:
    list_res = client.get("/api/delay/flights?limit=1")
    fid = list_res.json()["flights"][0]["flight_id"]

    res = client.get(f"/api/delay/flights/{fid}/alternatives")
    assert res.status_code == 200
    data = res.json()
    assert data["flight_id"] == fid
    assert "alternatives" in data
    for alt in data["alternatives"]:
        assert alt["origin_iata"] == data["origin_iata"]
        assert alt["destination_iata"] == data["destination_iata"]
        assert alt["flight_id"] != fid


def test_delay_what_if_scenario_prediction(client: TestClient) -> None:
    list_res = client.get("/api/delay/flights?limit=1")
    fid = list_res.json()["flights"][0]["flight_id"]

    payload = {
        "flight_id": fid,
        "inbound_delay_minutes": 55.0,
        "departure_queue_additional": 8,
        "weather_severity_override": 0.9,
        "slot_delay_minutes": 10.0,
    }
    res = client.post("/api/delay/predict", json=payload)
    assert res.status_code == 200
    data = res.json()

    assert data["predicted_delay_minutes"] >= 55.0
    assert data["status"] == "SIGNIFICANT_DELAY_LIKELY"
    assert data["severity"] == "HIGH"

    # Confirm inbound factor exists and reflects override
    inbound_factor = next((f for f in data["factors"] if f["category"] == "INBOUND"), None)
    assert inbound_factor is not None
    assert inbound_factor["impact_minutes"] == 55.0


def test_delay_dashboard_and_readiness_report(client: TestClient) -> None:
    dash_res = client.get("/api/delay/dashboard?sample_size=40")
    assert dash_res.status_code == 200
    dash = dash_res.json()
    assert dash["total_flights_monitored"] == 40
    assert "flights_requiring_attention" in dash
    assert "factor_breakdown" in dash
    assert "delay_distribution" in dash

    readiness_res = client.get("/api/delay/readiness")
    assert readiness_res.status_code == 200
    readiness = readiness_res.json()
    assert readiness["status"] == "DEMONSTRATION_READY"
    assert len(readiness["missing_operational_labels"]) >= 4
    assert len(readiness["requirements_for_production"]) >= 3


def test_delay_invalid_flight_404(client: TestClient) -> None:
    res = client.get("/api/delay/flights/NONEXISTENT_TRACK_999")
    assert res.status_code == 404

