"""Operational Stage Timeline Builder (8 Chronological Stages of Departure)."""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any

from app.schemas.delay import OperationalStage


class OperationalTimelineBuilder:
    """Builds the 8-stage operational departure timeline for flight delay investigations."""

    @staticmethod
    def build_timeline(
        flight: dict[str, Any],
        estimate_data: dict[str, Any],
        weather: dict[str, Any],
    ) -> list[OperationalStage]:
        stages: list[OperationalStage] = []
        sched_dep: datetime = flight["scheduled_departure_utc"]
        gate_delay = estimate_data.get("predicted_delay_minutes", 0.0)
        est_gate = estimate_data.get("estimated_gate_departure_utc", sched_dep)
        est_takeoff = estimate_data.get("estimated_takeoff_utc", est_gate + timedelta(minutes=15))
        tail = flight.get("aircraft_tail", "SF0001")
        has_inbound = flight.get("inbound_flight_id") is not None
        inbound_cs = flight.get("inbound_callsign")
        inbound_arr = flight.get("inbound_arrival_utc")
        inbound_delay = estimate_data.get("inbound_delay_minutes", 0.0)
        buffer_min = flight.get("turnaround_buffer_min", 90.0)
        wx_cond = weather.get("condition", "Fair / VFR Clear")
        queue_size = estimate_data.get("departure_queue_size", 3)
        taxi_min = estimate_data.get("taxi_time_minutes", 15.0)

        # STAGE 1: Scheduled Flight
        stages.append(
            OperationalStage(
                stage_number=1,
                stage_id="STAGE_1_SCHEDULE",
                stage_name="Scheduled Flight Baseline",
                status="COMPLETED",
                timestamp_utc=sched_dep,
                time_display=sched_dep.strftime("%I:%M %p UTC"),
                evidence_status="CONFIRMED",
                source="Airway Timetable & Master Schedule",
                explanation=f"Flight {flight['flight_number']} scheduled for {flight['origin_iata']} -> {flight['destination_iata']} departure at {sched_dep.strftime('%H:%M UTC')}.",
                is_confirmed=True,
            )
        )

        # STAGE 2: Incoming Aircraft
        if has_inbound and inbound_arr:
            inbound_status = "DELAYED" if inbound_delay > 10 else "COMPLETED"
            stages.append(
                OperationalStage(
                    stage_number=2,
                    stage_id="STAGE_2_INCOMING",
                    stage_name="Inbound Aircraft Arrival",
                    status=inbound_status,
                    timestamp_utc=inbound_arr,
                    time_display=inbound_arr.strftime("%I:%M %p UTC"),
                    evidence_status="CONFIRMED" if inbound_delay == 0 else "MODEL_INFERRED",
                    source=f"Flight Tracker (Rotation for {tail})",
                    explanation=(
                        f"Inbound flight {inbound_cs or 'previous leg'} touched down at {inbound_arr.strftime('%H:%M UTC')}. "
                        f"{'Turnaround buffer constrained.' if inbound_delay > 0 else 'Arrived with ample turnaround window.'}"
                    ),
                    is_confirmed=(inbound_delay == 0),
                )
            )
        else:
            stages.append(
                OperationalStage(
                    stage_number=2,
                    stage_id="STAGE_2_INCOMING",
                    stage_name="Inbound Aircraft Arrival",
                    status="COMPLETED",
                    timestamp_utc=sched_dep - timedelta(hours=2),
                    time_display="Overnight Stand",
                    evidence_status="CONFIRMED",
                    source="Fleet Stand Allocation",
                    explanation=f"Airframe {tail} originated from base or was positioned on stand overnight. No inbound rotation delay.",
                    is_confirmed=True,
                )
            )

        # STAGE 3: Ground Turnaround & Readiness
        turnaround_status = "DELAYED" if inbound_delay > 0 else "ACTIVE"
        stages.append(
            OperationalStage(
                stage_number=3,
                stage_id="STAGE_3_TURNAROUND",
                stage_name="Ground Turnaround & Servicing",
                status=turnaround_status,
                timestamp_utc=sched_dep - timedelta(minutes=30),
                time_display=f"{buffer_min:.0f}m Buffer",
                evidence_status="MODEL_INFERRED",
                source="Aviation Decision Support Model",
                explanation=(
                    f"Turnaround buffer: {buffer_min:.0f} min available. "
                    "Note: Baggage loading and cabin servicing are estimated from fleet turnaround parameters (sensor telemetry unavailable)."
                ),
                is_confirmed=False,
            )
        )

        # STAGE 4: Weather & Airport Conditions
        wx_status = "DELAYED" if weather.get("severity_index", 0) > 0.4 else "COMPLETED"
        stages.append(
            OperationalStage(
                stage_number=4,
                stage_id="STAGE_4_WEATHER",
                stage_name="Departure Weather & Surface Conditions",
                status=wx_status,
                timestamp_utc=sched_dep - timedelta(minutes=20),
                time_display=wx_cond,
                evidence_status="CONFIRMED",
                source="Open-Meteo Atmospheric Grid (Cell 2°)",
                explanation=(
                    f"Conditions at {flight['origin_iata']}: {wx_cond}. "
                    f"Rain: {weather.get('precipitation_mm', 0)} mm, Gusts: {weather.get('wind_gusts_ms', 0)} m/s, Temp: {weather.get('temperature_c', 24)}°C."
                ),
                is_confirmed=True,
            )
        )

        # STAGE 5: Airspace Capacity & Sequencing
        queue_status = "DELAYED" if queue_size > 5 else "ACTIVE"
        stages.append(
            OperationalStage(
                stage_number=5,
                stage_id="STAGE_5_AIRSPACE",
                stage_name="Airspace Capacity & Departure Slot",
                status=queue_status,
                timestamp_utc=sched_dep - timedelta(minutes=10),
                time_display=f"Queue: {queue_size} Acft",
                evidence_status="MODEL_INFERRED",
                source="Sky Force Sector Congestion Classifier",
                explanation=f"{queue_size} aircraft in departure bank at {flight['origin_iata']}. Airway slot sequencing allocated.",
                is_confirmed=False,
            )
        )

        # STAGE 6: Estimated Gate Departure (Off-Block)
        gate_status = "DELAYED" if gate_delay >= 15 else "PROJECTED"
        stages.append(
            OperationalStage(
                stage_number=6,
                stage_id="STAGE_6_GATE_DEP",
                stage_name="Estimated Gate Departure (Pushback)",
                status=gate_status,
                timestamp_utc=est_gate,
                time_display=est_gate.strftime("%I:%M %p UTC"),
                evidence_status="MODEL_INFERRED",
                source="Sky Force Departure Delay Estimator",
                explanation=(
                    f"Estimated off-block pushback at {est_gate.strftime('%H:%M UTC')} "
                    f"({'+' + str(round(gate_delay)) + 'm delay' if gate_delay > 0 else 'On Schedule'})."
                ),
                is_confirmed=False,
            )
        )

        # STAGE 7: Taxi & Runway Take-off
        stages.append(
            OperationalStage(
                stage_number=7,
                stage_id="STAGE_7_TAKEOFF",
                stage_name="Taxi-Out & Runway Take-Off",
                status="PROJECTED",
                timestamp_utc=est_takeoff,
                time_display=est_takeoff.strftime("%I:%M %p UTC"),
                evidence_status="MODEL_INFERRED",
                source="Kinematic Surface & Runway Model",
                explanation=(
                    f"Estimated runway takeoff at {est_takeoff.strftime('%H:%M UTC')} "
                    f"following {taxi_min:.0f} min taxi-out and departure hold."
                ),
                is_confirmed=False,
            )
        )

        # STAGE 8: Final Status & Outcome
        final_status = estimate_data.get("status", "ON_SCHEDULE")
        stages.append(
            OperationalStage(
                stage_number=8,
                stage_id="STAGE_8_OUTCOME",
                stage_name="Current Operational Assessment",
                status="ACTIVE" if final_status == "ON_SCHEDULE" else "DELAYED",
                timestamp_utc=sched_dep,
                time_display=final_status.replace("_", " "),
                evidence_status="MODEL_INFERRED",
                source="Sky Force Multi-Role Intelligence Service",
                explanation=estimate_data.get("explanation_plain_english", "Operational assessment ready."),
                is_confirmed=False,
            )
        )

        return stages

