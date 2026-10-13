"""Tests for Closest Point of Approach (CPA) and conflict proximity analysis."""
from __future__ import annotations

from datetime import datetime, timezone
import pytest

from app.services.conflict_analysis.cpa import (
    AircraftState,
    compute_pairwise_cpa,
    scan_airspace_conflicts,
)


def test_head_on_collision_course_cpa():
    # Two aircraft flying towards each other along latitude 20.0
    # AC1: at lon 70.0 heading East (90 deg) at 200 m/s (~720 km/h)
    # AC2: at lon 70.3 (~31 km away) heading West (270 deg) at 200 m/s
    t0 = datetime.now(timezone.utc)
    ac1 = AircraftState(
        aircraft_id="AC1",
        callsign="AI101",
        timestamp_utc=t0,
        latitude=20.0,
        longitude=70.0,
        altitude_m=10000.0,
        ground_speed_mps=200.0,
        heading_deg=90.0,
        vertical_rate_mps=0.0,
    )
    ac2 = AircraftState(
        aircraft_id="AC2",
        callsign="6E202",
        timestamp_utc=t0,
        latitude=20.0,
        longitude=70.3,
        altitude_m=10000.0,
        ground_speed_mps=200.0,
        heading_deg=270.0,
        vertical_rate_mps=0.0,
    )

    ev = compute_pairwise_cpa(ac1, ac2, horizon_s=300.0, horiz_thresh_km=9.26, vert_thresh_m=300.0)
    assert ev is not None
    # They should reach CPA within the 300s window
    assert 0.0 < ev.cpa_time_seconds < 150.0
    # Min distance should be near 0 horizontally and vertically
    assert ev.cpa_horizontal_dist_km < 2.0
    assert ev.severity == "HIGH"
    assert ev.is_projected is True


def test_parallel_well_separated_flights():
    # AC1 and AC2 50 km apart flying parallel North
    t0 = datetime.now(timezone.utc)
    ac1 = AircraftState(
        aircraft_id="AC1",
        callsign="AI101",
        timestamp_utc=t0,
        latitude=20.0,
        longitude=70.0,
        altitude_m=10000.0,
        ground_speed_mps=200.0,
        heading_deg=0.0,
        vertical_rate_mps=0.0,
    )
    ac2 = AircraftState(
        aircraft_id="AC2",
        callsign="6E202",
        timestamp_utc=t0,
        latitude=20.0,
        longitude=70.5,  # ~52 km East
        altitude_m=10000.0,
        ground_speed_mps=200.0,
        heading_deg=0.0,
        vertical_rate_mps=0.0,
    )

    ev = compute_pairwise_cpa(ac1, ac2, horizon_s=300.0, horiz_thresh_km=9.26, vert_thresh_m=300.0)
    assert ev is None  # No proximity within 9.26 km


def test_missing_altitude_flags_uncertainty():
    t0 = datetime.now(timezone.utc)
    ac1 = AircraftState(
        aircraft_id="AC1",
        callsign="AI101",
        timestamp_utc=t0,
        latitude=20.0,
        longitude=70.0,
        altitude_m=None,  # Missing altitude
        ground_speed_mps=200.0,
        heading_deg=90.0,
        vertical_rate_mps=0.0,
        uncertainty_flags=["MISSING_ALTITUDE"],
    )
    ac2 = AircraftState(
        aircraft_id="AC2",
        callsign="6E202",
        timestamp_utc=t0,
        latitude=20.0,
        longitude=70.05,  # ~5 km away
        altitude_m=10000.0,
        ground_speed_mps=200.0,
        heading_deg=90.0,
        vertical_rate_mps=0.0,
    )

    ev = compute_pairwise_cpa(ac1, ac2, horizon_s=300.0, horiz_thresh_km=9.26, vert_thresh_m=300.0)
    assert ev is not None
    assert "missing_altitude_on_one_or_both_aircraft" in ev.data_uncertainty_flags


def test_scan_airspace_conflicts_multi_aircraft():
    t0 = datetime.now(timezone.utc)
    states = [
        AircraftState("A1", "C1", t0, 20.0, 70.0, 10000.0, 200.0, 90.0, 0.0),
        AircraftState("A2", "C2", t0, 20.0, 70.1, 10000.0, 200.0, 270.0, 0.0),
        AircraftState("A3", "C3", t0, 25.0, 80.0, 11000.0, 220.0, 0.0, 0.0),
    ]
    events = scan_airspace_conflicts(states, horizon_s=300.0, horiz_thresh_km=15.0)
    assert len(events) >= 1
    assert any(e.aircraft_1 in ("A1", "A2") and e.aircraft_2 in ("A1", "A2") for e in events)
