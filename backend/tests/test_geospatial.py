"""Tests for geospatial geodesy, ENU transforms, and grid indexing."""
from __future__ import annotations

import math
import pytest

from app.services.geospatial.geo import (
    haversine_km,
    initial_bearing_deg,
    destination_point,
    interpolate_gc,
    sample_segment,
    local_enu_km,
)
from app.services.geospatial.grid import Grid


def test_haversine_delhi_mumbai():
    # Delhi (VIDP): 28.5665, 77.1031
    # Mumbai (VABB): 19.0887, 72.8679
    d = haversine_km(28.5665, 77.1031, 19.0887, 72.8679)
    # Expected great-circle distance is ~1138 km
    assert 1130.0 < d < 1150.0


def test_haversine_zero_distance():
    assert haversine_km(25.0, 75.0, 25.0, 75.0) == 0.0


def test_initial_bearing():
    # Due North: 0 deg
    b_north = initial_bearing_deg(10.0, 70.0, 20.0, 70.0)
    assert abs(b_north - 0.0) < 1e-3

    # Due East along equator: 90 deg
    b_east = initial_bearing_deg(0.0, 70.0, 0.0, 80.0)
    assert abs(b_east - 90.0) < 1e-3


def test_destination_and_interpolation():
    lat1, lon1 = 20.0, 75.0
    lat2, lon2 = destination_point(lat1, lon1, 90.0, 111.0)
    assert lat2 == pytest.approx(20.0, abs=0.1)
    assert lon2 > lon1

    # GC interpolation at midpoint
    mid_lat, mid_lon = interpolate_gc(lat1, lon1, lat2, lon2, 0.5)
    assert lon1 < mid_lon < lat2 or lon1 < mid_lon < lon2

    # sample_segment
    pts = sample_segment(lat1, lon1, lat2, lon2, step_km=25.0)
    assert len(pts) >= 2


def test_local_enu():
    lat0, lon0 = 20.0, 75.0
    # Origin should be (0, 0)
    dx0, dy0 = local_enu_km(lat0, lon0, lat0, lon0)
    assert abs(dx0) < 1e-4
    assert abs(dy0) < 1e-4

    # Point north
    dx_n, dy_n = local_enu_km(21.0, 75.0, lat0, lon0)
    assert abs(dx_n) < 1e-4
    assert dy_n > 100.0  # 1 deg latitude is ~111 km


def test_grid_indexing():
    grid = Grid(lat_min=10.0, lat_max=30.0, lon_min=70.0, lon_max=90.0, deg=2.0)
    cell = grid.cell_id(15.5, 73.2)
    assert cell == "R02C01"

    # Outside grid
    assert grid.cell_id(5.0, 70.0) is None
    assert grid.cell_id(15.0, 95.0) is None
