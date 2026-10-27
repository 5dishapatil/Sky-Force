"""Flight Departure Delay Estimator with strict evidence status and horizon-calibrated uncertainty."""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone, timedelta
from typing import Any

from app.schemas.delay import DelayContributingFactor, FlightSummary, FlightDetail


class BaseDelayEstimator(ABC):
    """Abstract interface for flight departure delay estimators."""

    @abstractmethod
    def estimate(
        self,
        flight: dict[str, Any],
        weather: dict[str, Any],
        queue_size: int,
        corridor_congestion: str,
        inbound_delay_override: float | None = None,
        queue_additional: int = 0,
        weather_override: float | None = None,
        slot_delay_override: float = 0.0,
    ) -> dict[str, Any]:
        """Compute departure delay, intervals, factors, and distinguished gate/takeoff timestamps."""
        pass


class DemonstrationDelayEstimator(BaseDelayEstimator):
    """Deterministic demonstration delay estimator using explicit aviation scenario assumptions.
    
    Adheres strictly to research guidelines:
    - Transparent about demonstration/simulation nature.
    - Explicitly separates scheduled gate departure, estimated off-block, and runway takeoff.
    - Categorizes factors as CONFIRMED, MODEL_INFERRED, or UNAVAILABLE.
    - Calibrates prediction intervals according to forecast horizon.
    """

    def __init__(self) -> None:
        self.standard_turnaround_min = 45.0  # standard for narrowbody A320/B737
        self.major_hub_nodes = {"VIDP", "VABB", "VOBL", "VOHS", "VOMM", "VECC"}

    def estimate(
        self,
        flight: dict[str, Any],
        weather: dict[str, Any],
        queue_size: int,
        corridor_congestion: str,
        inbound_delay_override: float | None = None,
        queue_additional: int = 0,
        weather_override: float | None = None,
        slot_delay_override: float = 0.0,
    ) -> dict[str, Any]:
        scheduled_dep = flight["scheduled_departure_utc"]
        orig_id = flight["origin_id"]
        is_major_hub = orig_id in self.major_hub_nodes

        # 1. Inbound Aircraft & Turnaround Factor
        turnaround_buffer = flight.get("turnaround_buffer_min", 90.0)
        has_inbound = flight.get("inbound_flight_id") is not None

        if inbound_delay_override is not None:
            inbound_delay = max(0.0, float(inbound_delay_override))
            inbound_evidence = "MODEL_INFERRED"
        elif has_inbound:
            # If buffer is less than standard turnaround, deficit propagates as delay
            if turnaround_buffer < self.standard_turnaround_min:
                inbound_delay = self.standard_turnaround_min - turnaround_buffer
                inbound_evidence = "MODEL_INFERRED"
            else:
                inbound_delay = 0.0
                inbound_evidence = "CONFIRMED"
        else:
            inbound_delay = 0.0
            inbound_evidence = "CONFIRMED"

        # 2. Local Airport Departure Queue / Metering
        effective_queue = max(1, queue_size + queue_additional)
        base_taxi = 16.0 if is_major_hub else 10.0
        queue_delay = max(0.0, (effective_queue - 4) * 1.8) if effective_queue > 4 else 0.0

        # 3. Weather Conditions at Departure Airport
        wx_severity = weather_override if weather_override is not None else weather.get("severity_index", 0.0)
        precip = weather.get("precipitation_mm", 0.0)
        gusts = weather.get("wind_gusts_ms", 0.0)

        wx_delay = 0.0
        if wx_severity > 0.6 or precip > 10.0:
            wx_delay = 25.0 + (wx_severity * 20.0)
        elif wx_severity > 0.3 or precip > 2.0 or gusts > 12.0:
            wx_delay = 10.0 + (wx_severity * 15.0)

        # 4. Airspace / En-Route Corridor Congestion
        cong_class = corridor_congestion.upper()
        congestion_delay = slot_delay_override
        if cong_class == "HIGH":
            congestion_delay += 15.0
        elif cong_class == "MEDIUM":
            congestion_delay += 6.0

        # Composite Departure Delay (at Gate / Off-Block)
        # Note: Inbound delay and weather are primary gate constraints; queue affects pushback-to-runway
        gate_delay = inbound_delay + (wx_delay * 0.7) + (congestion_delay * 0.5)
        gate_delay = max(0.0, round(gate_delay, 1))

        taxi_time = round(base_taxi + queue_delay + (wx_delay * 0.3), 1)
        total_delay = round(gate_delay + max(0.0, taxi_time - base_taxi), 1)

        # Forecast Horizon & Calibrated Interval
        # Horizon = time remaining between now and scheduled departure
        now_utc = datetime.now(timezone.utc)
        hours_to_dep = (scheduled_dep - now_utc).total_seconds() / 3600.0

        if hours_to_dep > 24:
            interval_half = 20.0
            confidence = 0.60
            conf_label = "LOW"
        elif hours_to_dep > 4:
            interval_half = 12.0
            confidence = 0.75
            conf_label = "MEDIUM"
        else:
            interval_half = 6.0
            confidence = 0.88
            conf_label = "HIGH"

        # Expand interval if high weather severity
        if wx_severity > 0.5:
            interval_half += 8.0
            confidence = max(0.5, confidence - 0.15)

        delay_min_bound = max(0.0, round(gate_delay - interval_half, 0))
        delay_max_bound = max(delay_min_bound + 5.0, round(gate_delay + interval_half, 0))

        # Status & Severity
        if gate_delay < 15.0:
            status = "ON_SCHEDULE"
            severity = "NOMINAL"
        elif gate_delay < 45.0:
            status = "DELAY_LIKELY"
            severity = "MODERATE"
        else:
            status = "SIGNIFICANT_DELAY_LIKELY"
            severity = "HIGH"

        # Timestamps
        est_gate_dep = scheduled_dep + timedelta(minutes=gate_delay)
        est_takeoff = est_gate_dep + timedelta(minutes=taxi_time)
        enroute_time = flight.get("enroute_eta_min", 75.0)
        sched_arrival = scheduled_dep + timedelta(minutes=enroute_time + base_taxi)
        est_arrival = est_takeoff + timedelta(minutes=enroute_time)

        # Factor Decomposition with explicit evidence sources
        factors: list[DelayContributingFactor] = []

        if inbound_delay > 0:
            factors.append(
                DelayContributingFactor(
                    name="Inbound Aircraft Rotation Delay",
                    category="INBOUND",
                    impact_minutes=round(inbound_delay, 1),
                    evidence_status=inbound_evidence,
                    description=(
                        f"Assigned aircraft {flight.get('aircraft_tail')} arrived with limited turnaround buffer "
                        f"({round(turnaround_buffer, 1)} min available vs {self.standard_turnaround_min} min required)."
                    ),
                    source="Synthetic Flight Schedule & Rotation Tracker",
                )
            )

        if wx_delay > 0:
            factors.append(
                DelayContributingFactor(
                    name="Departure Airport Weather Impact",
                    category="WEATHER",
                    impact_minutes=round(wx_delay, 1),
                    evidence_status="MODEL_INFERRED",
                    description=(
                        f"{weather.get('condition', 'Adverse weather')} at {flight['origin_iata']} "
                        f"(rain: {weather.get('precipitation_mm', 0)} mm, gusts: {weather.get('wind_gusts_ms', 0)} m/s)."
                    ),
                    source="Open-Meteo Archive / Gridded Atmospheric Model",
                )
            )

        if queue_delay > 0 or effective_queue > 4:
            factors.append(
                DelayContributingFactor(
                    name="Airport Departure Queue Sequencing",
                    category="QUEUE",
                    impact_minutes=round(queue_delay, 1),
                    evidence_status="MODEL_INFERRED",
                    description=f"{effective_queue} active flights scheduled in 30-min departure window at {flight['origin_iata']}.",
                    source="Airport Collaborative Flow Model",
                )
            )

        if congestion_delay > 0:
            factors.append(
                DelayContributingFactor(
                    name="En-Route Corridor Capacity Metering",
                    category="AIRSPACE",
                    impact_minutes=round(congestion_delay, 1),
                    evidence_status="MODEL_INFERRED",
                    description=f"Initial departure sector predicted in {cong_class} traffic density.",
                    source="RandomForest Congestion Classifier (3-Class)",
                )
            )

        # Unavailable factors (clearly noted to avoid false claims)
        factors.append(
            DelayContributingFactor(
                name="Ground Handling & Turnaround Progress",
                category="TURNAROUND",
                impact_minutes=0.0,
                evidence_status="UNAVAILABLE",
                description="Baggage loading, cabin cleaning, and fueling milestones are not monitored in surveillance telemetry.",
                source="Airline Ground Operations (Not Connected)",
            )
        )

        factors.append(
            DelayContributingFactor(
                name="Passenger Boarding Scanner Completion",
                category="UNKNOWN",
                impact_minutes=0.0,
                evidence_status="UNAVAILABLE",
                description="Gate scanner boarding counts are proprietary airline data and unavailable in open feeds.",
                source="DCS Departure Control System (Not Connected)",
            )
        )

        # Plain English summary for passengers
        if status == "ON_SCHEDULE":
            plain_english = (
                f"Flight {flight['flight_number']} is currently expected to depart on schedule at "
                f"{scheduled_dep.strftime('%I:%M %p')}. Inbound aircraft is on track with normal turnaround."
            )
        elif status == "DELAY_LIKELY":
            primary_reason = factors[0].name.lower() if factors else "operational sequencing"
            plain_english = (
                f"Flight {flight['flight_number']} is estimated to depart between "
                f"{delay_min_bound:.0f} and {delay_max_bound:.0f} minutes past schedule "
                f"(approx. {est_gate_dep.strftime('%I:%M %p')}). Primary contributing factor: {primary_reason}."
            )
        else:
            plain_english = (
                f"Significant delay likely for Flight {flight['flight_number']} (estimated {gate_delay:.0f} mins delay). "
                f"Expected pushback around {est_gate_dep.strftime('%I:%M %p')}. Please check gate monitors."
            )

        return {
            "predicted_delay_minutes": gate_delay,
            "delay_interval_min": delay_min_bound,
            "delay_interval_max": delay_max_bound,
            "status": status,
            "severity": severity,
            "confidence_score": confidence,
            "confidence_label": conf_label,
            "estimated_gate_departure_utc": est_gate_dep,
            "estimated_takeoff_utc": est_takeoff,
            "scheduled_arrival_utc": sched_arrival,
            "estimated_arrival_utc": est_arrival,
            "taxi_time_minutes": taxi_time,
            "inbound_delay_minutes": inbound_delay,
            "turnaround_buffer_minutes": turnaround_buffer,
            "factors": factors,
            "departure_queue_size": effective_queue,
            "explanation_plain_english": plain_english,
        }

