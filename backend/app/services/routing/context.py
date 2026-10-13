"""Per-edge routing context: the attribute values that feed the cost model.

Every value carries its provenance (``*_source``) so that a heuristic is never
presented as a model prediction and a missing input is never presented as an
observation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class EdgeAttrs:
    edge_id: str
    distance_km: float
    time_min: float
    time_source: str
    weather_severity: float | None = None
    weather_source: str = "unavailable"
    congestion_score: float | None = None
    congestion_class: str | None = None
    congestion_probs: dict[str, float] | None = None
    congestion_source: str = "unavailable"
    uncertainty: float = 0.0
    closed: bool = False
    closure_reasons: list[str] = field(default_factory=list)
    event_ids: list[str] = field(default_factory=list)
    flags: list[str] = field(default_factory=list)

    def copy(self) -> "EdgeAttrs":
        return EdgeAttrs(**{**self.__dict__, "closure_reasons": list(self.closure_reasons),
                            "event_ids": list(self.event_ids), "flags": list(self.flags),
                            "congestion_probs": dict(self.congestion_probs) if self.congestion_probs else None})


@dataclass
class RoutingContext:
    scenario_time: datetime
    scenario_id: str | None
    edges: dict[tuple[str, str], EdgeAttrs]
    sources: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    active_events: list[dict[str, Any]] = field(default_factory=list)

    def copy(self) -> "RoutingContext":
        return RoutingContext(self.scenario_time, self.scenario_id, {k: v.copy() for k, v in self.edges.items()},
                              dict(self.sources), list(self.warnings), list(self.active_events))

    @property
    def v_max_km_per_min(self) -> float:
        """Upper bound on (distance / time) over all edges: makes the A* time term admissible."""
        vals = [a.distance_km / a.time_min for a in self.edges.values() if a.time_min > 0]
        return max(vals) if vals else 1e9
