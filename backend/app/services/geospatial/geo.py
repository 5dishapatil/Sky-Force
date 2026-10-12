"""Spherical geodesy helpers.

Horizontal distances use the haversine formula on a sphere of mean Earth
radius (IUGG R1 = 6371.0088 km). Haversine distances satisfy the triangle
inequality exactly, which the A* heuristic relies on (see routing/search.py).
Ellipsoidal WGS-84 distances (pyproj) differ by < 0.5 % and are used in the
unit tests as an independent cross-check.

Note: a great-circle distance is NOT the distance an aircraft actually flies.
"""
from __future__ import annotations

import math

import numpy as np

EARTH_RADIUS_KM = 6371.0088
KM_PER_NM = 1.852


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = p2 - p1
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(min(1.0, math.sqrt(a)))


def haversine_km_vec(lat1, lon1, lat2, lon2):  # noqa: ANN001, ANN201
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_KM * np.arcsin(np.minimum(1.0, np.sqrt(a)))


def initial_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360.0) % 360.0


def interpolate_gc(lat1: float, lon1: float, lat2: float, lon2: float, f: float) -> tuple[float, float]:
    """Point at fraction ``f`` along the great circle between two points."""
    p1, l1, p2, l2 = map(math.radians, (lat1, lon1, lat2, lon2))
    d = haversine_km(lat1, lon1, lat2, lon2) / EARTH_RADIUS_KM
    if d < 1e-12:
        return lat1, lon1
    a = math.sin((1 - f) * d) / math.sin(d)
    b = math.sin(f * d) / math.sin(d)
    x = a * math.cos(p1) * math.cos(l1) + b * math.cos(p2) * math.cos(l2)
    y = a * math.cos(p1) * math.sin(l1) + b * math.cos(p2) * math.sin(l2)
    z = a * math.sin(p1) + b * math.sin(p2)
    return math.degrees(math.atan2(z, math.hypot(x, y))), math.degrees(math.atan2(y, x))


def sample_segment(lat1: float, lon1: float, lat2: float, lon2: float, step_km: float = 25.0) -> list[tuple[float, float]]:
    d = haversine_km(lat1, lon1, lat2, lon2)
    n = max(2, int(math.ceil(d / step_km)) + 1)
    return [interpolate_gc(lat1, lon1, lat2, lon2, i / (n - 1)) for i in range(n)]


def destination_point(lat: float, lon: float, bearing_deg: float, dist_km: float) -> tuple[float, float]:
    p1, l1, b = math.radians(lat), math.radians(lon), math.radians(bearing_deg)
    d = dist_km / EARTH_RADIUS_KM
    p2 = math.asin(math.sin(p1) * math.cos(d) + math.cos(p1) * math.sin(d) * math.cos(b))
    l2 = l1 + math.atan2(math.sin(b) * math.sin(d) * math.cos(p1), math.cos(d) - math.sin(p1) * math.sin(p2))
    return math.degrees(p2), (math.degrees(l2) + 540.0) % 360.0 - 180.0


def angle_diff_deg(a: float, b: float) -> float:
    """Signed smallest difference a-b in degrees, range (-180, 180]."""
    d = (a - b + 180.0) % 360.0 - 180.0
    return 180.0 if d == -180.0 else d


def local_enu_km(lat: float, lon: float, lat0: float, lon0: float) -> tuple[float, float]:
    """Equirectangular local tangent-plane projection (east, north) in km.
    Adequate for the short ranges (< ~300 km) used by the proximity module."""
    x = math.radians(lon - lon0) * EARTH_RADIUS_KM * math.cos(math.radians(lat0))
    y = math.radians(lat - lat0) * EARTH_RADIUS_KM
    return x, y
