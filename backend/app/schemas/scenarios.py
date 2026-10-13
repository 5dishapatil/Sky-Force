"""Scenario management and event schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class ScenarioEventItem(BaseModel):
    id: str
    name: str
    description: str = ""
    event_type: str
    start_time_utc: datetime
    end_time_utc: datetime
    enabled: bool = True
    scope: dict[str, Any] = Field(default_factory=dict)
    severity: float = 1.0
    source_status: str = "user_defined_simulation"


class ScenarioItem(BaseModel):
    id: str
    name: str
    description: str = ""
    is_prebuilt: bool = False
    is_active: bool = False
    seed: int = 0
    scenario_time_utc: datetime
    created_at: datetime
    updated_at: datetime
    events: list[ScenarioEventItem] = Field(default_factory=list)


class CreateScenarioEventInput(BaseModel):
    name: str
    description: str = ""
    event_type: str
    start_time_utc: datetime
    end_time_utc: datetime
    enabled: bool = True
    scope: dict[str, Any] = Field(default_factory=dict)
    severity: float = 1.0
    source_status: str = "user_defined_simulation"


class CreateScenarioInput(BaseModel):
    name: str
    description: str = ""
    scenario_time_utc: datetime | None = None
    events: list[CreateScenarioEventInput] = Field(default_factory=list)


class DynamicRerouteRequest(BaseModel):
    scenario_id: str
    origin: str
    destination: str
    objective: str = "balanced"
    algorithm: str = "dijkstra"


class DynamicRerouteResponse(BaseModel):
    scenario_id: str
    scenario_name: str
    origin: str
    destination: str
    baseline_route: dict[str, Any]
    rerouted_route: dict[str, Any]
    delta: dict[str, Any]
    explanation: list[str]
    affected_events: list[dict[str, Any]]
