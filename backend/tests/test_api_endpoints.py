"""Integration tests for Sky Force REST API endpoints using TestClient."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    with TestClient(app) as c:
        yield c


def test_root_endpoint(client: TestClient):
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["project"] == "Sky Force"
    assert "disclaimer" in data


def test_health_endpoint(client: TestClient):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("ok", "degraded")
    assert "database" in data
    assert "disclaimer" in data


def test_airports_endpoint(client: TestClient):
    resp = client.get("/api/airports")
    assert resp.status_code == 200
    airports = resp.json()
    assert len(airports) >= 1
    # Check VIDP and VABB exist
    icaos = {a["node_id"] for a in airports}
    assert "VIDP" in icaos
    assert "VABB" in icaos


def test_airports_network(client: TestClient):
    resp = client.get("/api/airports/network")
    assert resp.status_code == 200
    net = resp.json()
    assert "airports" in net
    assert "edges" in net
    assert len(net["airports"]) > 0
    assert len(net["edges"]) > 0


def test_route_optimize(client: TestClient):
    payload = {
        "origin": "VIDP",
        "destination": "VABB",
        "algorithm": "dijkstra",
        "objective": "distance",
    }
    resp = client.post("/api/routes/optimize", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert res["found"] is True
    assert res["path"][0] == "VIDP"
    assert res["path"][-1] == "VABB"
    assert len(res["path"]) >= 2
    assert res["totals"]["distance_km"] > 500.0


def test_route_compare(client: TestClient):
    payload = {
        "origin": "VIDP",
        "destination": "VABB",
        "algorithm": "dijkstra",
        "objective": "balanced",
    }
    resp = client.post("/api/routes/compare", json=payload)
    assert resp.status_code == 200
    res = resp.json()
    assert "routes" in res
    assert len(res["routes"]) >= 1


def test_scenarios_listing(client: TestClient):
    resp = client.get("/api/scenarios")
    assert resp.status_code == 200
    scenarios = resp.json()
    assert len(scenarios) >= 1
    sc_ids = [s["id"] for s in scenarios]
    assert "clear" in sc_ids


def test_scenarios_activate_and_reset(client: TestClient):
    resp = client.post("/api/scenarios/corridor-congestion/activate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == "corridor-congestion"
    assert data["is_active"] is True

    # Reset
    resp2 = client.post("/api/scenarios/corridor-congestion/reset")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["is_active"] is False


def test_scenarios_reroute_endpoint(client: TestClient):
    payload = {
        "origin": "VIDP",
        "destination": "VABB",
        "scenario_id": "corridor-closure",
        "objective": "balanced",
        "algorithm": "dijkstra",
    }
    resp = client.post("/api/scenarios/reroute", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "baseline_route" in data
    assert "rerouted_route" in data
    assert "delta" in data
    assert "explanation" in data


def test_conflicts_latest(client: TestClient):
    resp = client.get("/api/conflicts/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert "aircraft_scanned" in data
    assert "events" in data
    assert "disclaimer" in data


def test_models_status_and_metrics(client: TestClient):
    resp = client.get("/api/models/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "operational"
    assert data["congestion_model"] is not None
    assert data["eta_model"] is not None

    resp_m = client.get("/api/models/metrics")
    assert resp_m.status_code == 200
    metrics = resp_m.json()
    assert "congestion" in metrics
    assert "eta" in metrics


def test_experiments_benchmark(client: TestClient):
    payload = {
        "od_pairs": [["VIDP", "VABB"]],
        "scenario_ids": ["clear", "corridor-congestion"],
        "algorithm": "dijkstra",
    }
    resp = client.post("/api/experiments/run", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert "experiment_id" in data
    assert data["status"] == "completed"
    assert data["total_evaluations"] >= 2
    assert "results" in data

    # Verify listing
    resp_list = client.get("/api/experiments")
    assert resp_list.status_code == 200
    runs = resp_list.json()
    assert len(runs) >= 1

