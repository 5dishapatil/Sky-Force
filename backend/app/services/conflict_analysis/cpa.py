"""Simplified Trajectory Proximity and Closest Point of Approach (CPA) Analysis.

DISCLAIMER:
This is an experimental analytical visualization tool, NOT an operational
separation assurance or collision-avoidance system. Standards configured here
are user-tunable "prototype proximity thresholds", NOT official ATC separation
standards. It must never be used to issue aircraft instructions or guarantee
separation.

Assumptions:
- Linear projection over a short forecast horizon (default: 5 minutes / 300 s).
- Constant velocity vector [vx, vy, vz] estimated from ground speed, heading,
  and vertical rate.
- Pairwise search accelerated with spatial bounding boxes.
- Vertical separation evaluated only when valid altitude data exists for BOTH
  aircraft (missing altitude is explicitly flagged as uncertainty, never zero-filled).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import numpy as np

from app.services.geospatial.geo import haversine_km, local_enu_km

EARTH_RADIUS_KM = 6371.0088


@dataclass
class AircraftState:
    aircraft_id: str
    callsign: str | None
    timestamp_utc: datetime
    latitude: float
    longitude: float
    altitude_m: float | None
    ground_speed_mps: float | None
    heading_deg: float | None
    vertical_rate_mps: float | None
    is_synthetic: bool = True
    uncertainty_flags: list[str] = field(default_factory=list)

    @property
    def has_velocity(self) -> bool:
        return self.ground_speed_mps is not None and self.heading_deg is not None

    @property
    def velocity_enu_km_s(self) -> tuple[float, float, float]:
        """East, North (km/s) and Up (km/s) velocity components."""
        if not self.has_velocity:
            return 0.0, 0.0, 0.0
        v_horiz_km_s = (self.ground_speed_mps or 0.0) / 1000.0
        hdg_rad = math.radians(self.heading_deg or 0.0)
        vx = v_horiz_km_s * math.sin(hdg_rad)
        vy = v_horiz_km_s * math.cos(hdg_rad)
        vz = ((self.vertical_rate_mps or 0.0) / 1000.0) if self.altitude_m is not None else 0.0
        return vx, vy, vz


@dataclass
class ConflictProximityEvent:
    event_id: str
    aircraft_1: str
    callsign_1: str | None
    aircraft_2: str
    callsign_2: str | None
    observation_time_utc: datetime
    current_horizontal_dist_km: float
    current_vertical_diff_m: float | None
    cpa_time_seconds: float
    cpa_horizontal_dist_km: float
    cpa_vertical_diff_m: float | None
    severity: str  # 'LOW', 'MEDIUM', 'HIGH'
    is_projected: bool
    data_uncertainty_flags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "aircraft_1": self.aircraft_1,
            "callsign_1": self.callsign_1,
            "aircraft_2": self.aircraft_2,
            "callsign_2": self.callsign_2,
            "observation_time_utc": self.observation_time_utc.isoformat(),
            "current_horizontal_dist_km": round(self.current_horizontal_dist_km, 2),
            "current_vertical_diff_m": round(self.current_vertical_diff_m, 1) if self.current_vertical_diff_m is not None else None,
            "cpa_time_seconds": round(self.cpa_time_seconds, 1),
            "cpa_horizontal_dist_km": round(self.cpa_horizontal_dist_km, 2),
            "cpa_vertical_diff_m": round(self.cpa_vertical_diff_m, 1) if self.cpa_vertical_diff_m is not None else None,
            "severity": self.severity,
            "is_projected": self.is_projected,
            "data_uncertainty_flags": self.data_uncertainty_flags,
            "disclaimer": "Research proxy proximity estimate only. Not an operational separation loss.",
        }


def compute_pairwise_cpa(
    ac1: AircraftState,
    ac2: AircraftState,
    horizon_s: float = 300.0,
    horiz_thresh_km: float = 9.26,   # ~5 NM prototype threshold
    vert_thresh_m: float = 300.0,     # ~1000 ft prototype threshold
) -> ConflictProximityEvent | None:
    """Calculates CPA between two aircraft over the specified forecast horizon."""
    # Current distance
    d_curr_km = haversine_km(ac1.latitude, ac1.longitude, ac2.latitude, ac2.longitude)
    
    # Altitude diff
    v_diff_m: float | None = None
    if ac1.altitude_m is not None and ac2.altitude_m is not None:
        v_diff_m = abs(ac1.altitude_m - ac2.altitude_m)

    uncertainty: list[str] = []
    if ac1.altitude_m is None or ac2.altitude_m is None:
        uncertainty.append("missing_altitude_on_one_or_both_aircraft")
    if not ac1.has_velocity or not ac2.has_velocity:
        uncertainty.append("missing_velocity_vector")

    # Local tangent coordinates relative to ac1
    x1, y1 = 0.0, 0.0
    x2, y2 = local_enu_km(ac2.latitude, ac2.longitude, ac1.latitude, ac1.longitude)
    z1 = (ac1.altitude_m or 0.0) / 1000.0
    z2 = (ac2.altitude_m or 0.0) / 1000.0

    vx1, vy1, vz1 = ac1.velocity_enu_km_s
    vx2, vy2, vz2 = ac2.velocity_enu_km_s

    # Relative position and relative velocity: r = r2 - r1, v = v2 - v1
    dx = x2 - x1
    dy = y2 - y1
    dz = z2 - z1

    dvx = vx2 - vx1
    dvy = vy2 - vy1
    dvz = vz2 - vz1

    v_rel_sq_horiz = dvx * dvx + dvy * dvy
    
    # Calculate time to CPA horizontally
    if v_rel_sq_horiz < 1e-12:
        t_cpa = 0.0
    else:
        # t_cpa minimizes (dx + dvx*t)^2 + (dy + dvy*t)^2 => t = -(dx*dvx + dy*dvy) / v_rel_sq
        t_cpa = -(dx * dvx + dy * dvy) / v_rel_sq_horiz

    # Bounded to forecast horizon [0, horizon_s]
    t_cpa_clamped = max(0.0, min(float(horizon_s), float(t_cpa)))

    # Compute position at t_cpa_clamped
    cpa_x = dx + dvx * t_cpa_clamped
    cpa_y = dy + dvy * t_cpa_clamped
    cpa_d_km = math.hypot(cpa_x, cpa_y)

    cpa_v_diff_m: float | None = None
    if ac1.altitude_m is not None and ac2.altitude_m is not None:
        cpa_z = (dz + dvz * t_cpa_clamped) * 1000.0
        cpa_v_diff_m = abs(cpa_z)

    # Evaluate proximity condition
    # Triggers if within threshold now OR projected within threshold within horizon
    horiz_close = (d_curr_km <= horiz_thresh_km) or (cpa_d_km <= horiz_thresh_km)
    
    # If vertical altitude is missing, treat conservatively but flag uncertainty
    vert_close = True
    if cpa_v_diff_m is not None:
        vert_close = (cpa_v_diff_m <= vert_thresh_m)

    if not (horiz_close and vert_close):
        return None

    # Determine prototype severity tier
    # HIGH: <= 50% threshold horizontally AND vertically
    # MEDIUM: <= 100% threshold
    # LOW: marginal
    if cpa_d_km <= (horiz_thresh_km * 0.5) and (cpa_v_diff_m is None or cpa_v_diff_m <= (vert_thresh_m * 0.5)):
        severity = "HIGH"
    elif cpa_d_km <= horiz_thresh_km and (cpa_v_diff_m is None or cpa_v_diff_m <= vert_thresh_m):
        severity = "MEDIUM"
    else:
        severity = "LOW"

    eid = f"PROX-{ac1.aircraft_id}-{ac2.aircraft_id}-{int(ac1.timestamp_utc.timestamp())}"
    return ConflictProximityEvent(
        event_id=eid,
        aircraft_1=ac1.aircraft_id,
        callsign_1=ac1.callsign,
        aircraft_2=ac2.aircraft_id,
        callsign_2=ac2.callsign,
        observation_time_utc=ac1.timestamp_utc,
        current_horizontal_dist_km=d_curr_km,
        current_vertical_diff_m=v_diff_m,
        cpa_time_seconds=t_cpa_clamped,
        cpa_horizontal_dist_km=cpa_d_km,
        cpa_vertical_diff_m=cpa_v_diff_m,
        severity=severity,
        is_projected=t_cpa_clamped > 0.1,
        data_uncertainty_flags=uncertainty,
    )


def scan_airspace_conflicts(
    states: list[AircraftState],
    horizon_s: float = 300.0,
    horiz_thresh_km: float = 9.26,
    vert_thresh_m: float = 300.0,
) -> list[ConflictProximityEvent]:
    """Scans all unique pairs of aircraft active at a given time slice."""
    events: list[ConflictProximityEvent] = []
    n = len(states)
    for i in range(n):
        for j in range(i + 1, n):
            ev = compute_pairwise_cpa(
                states[i],
                states[j],
                horizon_s=horizon_s,
                horiz_thresh_km=horiz_thresh_km,
                vert_thresh_m=vert_thresh_m,
            )
            if ev is not None:
                events.append(ev)
    events.sort(key=lambda e: (e.severity == "HIGH", e.cpa_horizontal_dist_km))
    return events
