"""Integration tests for multi-schema dataset upload, weather grid indexing, traffic-weather linking, and 3D visualization data contracts."""
import io
import pytest
import pandas as pd
from fastapi.testclient import TestClient

from app.main import app
from app.services.datasets.manager import DatasetManager
from app.services.datasets.schema_mapper import auto_detect_dataset_type, auto_detect_mapping, validate_mapping


@pytest.fixture
def client():
    return TestClient(app)


def test_schema_mapper_auto_detects_dataset_types():
    # 1. Aircraft surveillance
    aircraft_cols = ["icao24", "time", "lat", "lon", "velocity", "baro_altitude"]
    assert auto_detect_dataset_type(aircraft_cols) == "aircraft_observations"

    # 2. Weather observations
    weather_cols = ["lat", "lon", "valid_time", "precipitation_mm", "wind_gusts_10m_ms"]
    assert auto_detect_dataset_type(weather_cols) == "weather_observations"

    # 3. Pre-aggregated congestion
    congestion_cols = ["cell_id", "aircraft_count", "congestion_score", "predicted_class"]
    assert auto_detect_dataset_type(congestion_cols) == "congestion_cells"


def test_weather_observations_upload_and_pipeline(client):
    """Verifies that weather dataset upload recognizes the weather schema and executes weather indexing."""
    weather_csv = (
        "lat,lon,valid_time,precip_mm,wind_spd,gust\n"
        "28.55,77.10,2026-01-15 10:00:00,18.5,12.0,24.5\n"
        "28.60,77.15,2026-01-15 10:00:00,22.0,14.5,28.0\n"
        "19.08,72.87,2026-01-15 10:00:00,2.5,5.0,8.0\n"
        "12.97,77.59,2026-01-15 10:00:00,0.0,3.0,4.5\n"
    )

    # 1. Upload weather CSV
    files = {"file": ("india_monsoon_weather.csv", io.BytesIO(weather_csv.encode("utf-8")), "text/csv")}
    data = {"dataset_type": "weather_observations"}
    resp = client.post("/api/datasets/upload", files=files, data=data)
    assert resp.status_code == 200, resp.text
    wx_data = resp.json()

    assert wx_data["dataset_type"] == "weather_observations"
    assert wx_data["is_valid_format"] is True
    assert wx_data["suggested_mapping"]["precipitation_mm"] == "precip_mm"
    assert wx_data["suggested_mapping"]["latitude"] == "lat"
    assert wx_data["suggested_mapping"]["longitude"] == "lon"

    wx_id = wx_data["dataset_id"]

    # 2. Execute weather indexing pipeline
    pipe_resp = client.post(
        f"/api/datasets/{wx_id}/pipeline",
        json={"stages": ["validation", "weather_indexing"]},
    )
    assert pipe_resp.status_code == 200, pipe_resp.text
    pipe_data = pipe_resp.json()
    assert pipe_data["status"] == "completed"
    assert "weather_grid" in pipe_data["artifact_paths"]

    # Check stages
    stages = {s["stage"]: s for s in pipe_data["stages"]}
    assert "weather_indexing" in stages
    assert stages["weather_indexing"]["output_summary"]["spatial_cells_covered"] > 0
    assert stages["weather_indexing"]["output_summary"]["max_precipitation_mm"] >= 20.0


def test_preaggregated_congestion_cells_upload_and_pipeline(client):
    """Verifies that pre-aggregated congestion cell matrices are validated and registered."""
    congestion_csv = (
        "cell_id,aircraft_count,congestion_score,predicted_class\n"
        "IND_N_01,14,0.85,HIGH\n"
        "IND_N_02,8,0.50,MEDIUM\n"
        "IND_W_01,2,0.12,LOW\n"
        "IND_S_01,1,0.05,LOW\n"
    )

    files = {"file": ("delhi_corridor_congestion.csv", io.BytesIO(congestion_csv.encode("utf-8")), "text/csv")}
    data = {"dataset_type": "congestion_cells"}
    resp = client.post("/api/datasets/upload", files=files, data=data)
    assert resp.status_code == 200, resp.text
    cg_data = resp.json()

    assert cg_data["dataset_type"] == "congestion_cells"
    assert cg_data["is_valid_format"] is True
    cg_id = cg_data["dataset_id"]

    pipe_resp = client.post(
        f"/api/datasets/{cg_id}/pipeline",
        json={"stages": ["validation"]},
    )
    assert pipe_resp.status_code == 200, pipe_resp.text
    assert pipe_resp.json()["status"] == "completed"


def test_link_traffic_with_weather_and_route_awareness(client):
    """Verifies spatial/temporal linking of flight tracks with a measured weather dataset, and routing impact."""
    # 1. Upload aircraft CSV
    aircraft_csv = (
        "icao24,time,lat,lon,velocity,baro_altitude,callsign\n"
        "400a01,2026-01-15 10:00:00,28.55,77.10,210.0,6000.0,AIC101\n"
        "400a01,2026-01-15 10:01:00,28.20,76.80,215.0,6500.0,AIC101\n"
        "400a02,2026-01-15 10:00:00,19.08,72.87,190.0,4000.0,IGO202\n"
        "400a03,2026-01-15 10:00:00,12.97,77.59,200.0,5000.0,SEJ303\n"
    )
    ac_resp = client.post(
        "/api/datasets/upload",
        files={"file": ("flights_jan15.csv", io.BytesIO(aircraft_csv.encode("utf-8")), "text/csv")},
        data={"dataset_type": "aircraft_observations"},
    )
    assert ac_resp.status_code == 200
    ac_id = ac_resp.json()["dataset_id"]

    # 2. Upload weather CSV with severe storm in northern India (Delhi sector)
    weather_csv = (
        "latitude,longitude,valid_time_utc,precipitation_mm,wind_gusts_10m_ms\n"
        "28.55,77.10,2026-01-15 10:00:00,45.0,32.0\n"
        "28.20,76.80,2026-01-15 10:00:00,50.0,35.0\n"
        "19.08,72.87,2026-01-15 10:00:00,1.0,4.0\n"
        "12.97,77.59,2026-01-15 10:00:00,0.0,2.0\n"
    )
    wx_resp = client.post(
        "/api/datasets/upload",
        files={"file": ("storm_grid.csv", io.BytesIO(weather_csv.encode("utf-8")), "text/csv")},
        data={"dataset_type": "weather_observations"},
    )
    assert wx_resp.status_code == 200
    wx_id = wx_resp.json()["dataset_id"]

    # Run weather pipeline
    client.post(f"/api/datasets/{wx_id}/pipeline", json={"stages": ["validation", "weather_indexing"]})

    # Run aircraft pipeline
    client.post(f"/api/datasets/{ac_id}/pipeline", json={"stages": ["quality", "segmentation", "features", "inference"]})

    # 3. Link aircraft dataset with weather dataset
    link_resp = client.post(
        f"/api/datasets/{ac_id}/link-weather",
        json={"weather_dataset_id": wx_id, "spatial_tolerance_deg": 0.5, "temporal_tolerance_seconds": 3600},
    )
    assert link_resp.status_code == 200, link_resp.text
    link_data = link_resp.json()
    assert link_data["status"] == "linked"
    assert link_data["total_traffic_rows"] >= 3
    assert link_data["matched_rows"] >= 1
    assert link_data["coverage_percentage"] > 0

    # 4. Execute route optimization using this dataset
    opt_resp = client.post(
        "/api/routes/optimize",
        json={
            "origin": "VIDP",
            "destination": "VABB",
            "objective": "weather",
            "algorithm": "dijkstra",
            "dataset_id": ac_id,
        },
    )
    assert opt_resp.status_code == 200, opt_resp.text
    opt_data = opt_resp.json()
    assert opt_data["found"] is True
    assert opt_data["dataset_id"] == ac_id
    assert "cost_by_factor" in opt_data
    assert "weather" in opt_data["cost_by_factor"]
    assert opt_data["cost_by_factor"]["weather"] > 0
