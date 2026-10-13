"""Transparent, configurable multi-factor edge cost model.

    edge_cost = w_d * distance_c + w_t * time_c + w_w * weather_c + w_c * congestion_c + w_u * uncertainty_c
                + EPS * distance_c                          (strictly-positive tie-breaker)

Components are DIMENSIONLESS:
    distance_c    = distance_km / ref_km                       (ref_km = median edge length)
    time_c        = time_min / ref_min                         (ref_min = ref_km at the heuristic cruise speed)
    weather_c     = weather_severity[0..1]   * distance_km / ref_km   (severity-weighted length)
    congestion_c  = congestion_score[0..1]   * distance_km / ref_km
    uncertainty_c = uncertainty[0..1]        * distance_km / ref_km

Weights are validated (finite, >= 0, sum > 0) and normalised to sum to 1.
Closures are HARD constraints handled by the search (edge excluded), never a penalty.
A missing weather/congestion value contributes 0 to its component but raises the
uncertainty component and is flagged - it is never treated as an observation.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.core.errors import ValidationFailed
from app.services.routing.context import EdgeAttrs

FACTORS = ("distance", "time", "weather", "congestion", "uncertainty")
EPS = 1e-3

OBJECTIVE_PRESETS: dict[str, dict[str, float]] = {
    "distance": {"distance": 1.0, "time": 0, "weather": 0, "congestion": 0, "uncertainty": 0},
    "fastest": {"distance": 0, "time": 1.0, "weather": 0, "congestion": 0, "uncertainty": 0},
    "weather": {"distance": 0.5, "time": 0, "weather": 0.5, "congestion": 0, "uncertainty": 0},
    "congestion": {"distance": 0.5, "time": 0, "weather": 0, "congestion": 0.5, "uncertainty": 0},
    "balanced": {"distance": 0.25, "time": 0.25, "weather": 0.2, "congestion": 0.2, "uncertainty": 0.1},
}


@dataclass(frozen=True)
class CostWeights:
    distance: float = 0.25
    time: float = 0.25
    weather: float = 0.2
    congestion: float = 0.2
    uncertainty: float = 0.1

    @classmethod
    def from_dict(cls, d: dict[str, float]) -> "CostWeights":
        vals = {}
        for k in FACTORS:
            v = float(d.get(k, 0.0))
            if not math.isfinite(v) or v < 0:
                raise ValidationFailed(f"Weight '{k}' must be a finite number >= 0", details={"weight": k, "value": v})
            vals[k] = v
        total = sum(vals.values())
        if total <= 0:
            raise ValidationFailed("At least one weight must be > 0")
        return cls(**{k: v / total for k, v in vals.items()})

    @classmethod
    def preset(cls, objective: str) -> "CostWeights":
        if objective not in OBJECTIVE_PRESETS:
            raise ValidationFailed(f"Unknown objective '{objective}'", details={"allowed": list(OBJECTIVE_PRESETS)})
        return cls.from_dict(OBJECTIVE_PRESETS[objective])

    def as_dict(self) -> dict[str, float]:
        return {k: round(getattr(self, k), 6) for k in FACTORS}


class CostModel:
    def __init__(self, ref_km: float, ref_min: float):
        if ref_km <= 0 or ref_min <= 0:
            raise ValueError("reference scales must be positive")
        self.ref_km = ref_km
        self.ref_min = ref_min

    def components(self, a: EdgeAttrs) -> dict[str, float]:
        L = a.distance_km / self.ref_km
        return {
            "distance": L,
            "time": a.time_min / self.ref_min,
            "weather": (a.weather_severity or 0.0) * L,
            "congestion": (a.congestion_score or 0.0) * L,
            "uncertainty": a.uncertainty * L,
        }

    def weighted(self, comps: dict[str, float], w: CostWeights) -> dict[str, float]:
        return {k: getattr(w, k) * comps[k] for k in FACTORS}

    def edge_cost(self, a: EdgeAttrs, w: CostWeights) -> float:
        comps = self.components(a)
        cost = sum(self.weighted(comps, w).values()) + EPS * comps["distance"]
        if not math.isfinite(cost) or cost <= 0:
            raise ValidationFailed(f"Invalid non-positive cost on edge {a.edge_id}", details={"cost": cost})
        return cost

    def heuristic_coefficient(self, w: CostWeights, v_max_km_per_min: float) -> float:
        """Cost per great-circle km that is a guaranteed LOWER bound on any path's cost.

        * distance term: path length >= great-circle distance (triangle inequality of haversine);
        * time term: each edge time >= edge_km / v_max, so path time >= gc / v_max;
        * weather / congestion / uncertainty terms are >= 0 and are omitted (bounded below by 0).
        Hence h(n) = coef * gc(n, goal) is admissible and consistent.
        """
        return (w.distance + EPS) / self.ref_km + w.time / (v_max_km_per_min * self.ref_min)
