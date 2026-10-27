"""Data Readiness & Gap Analysis Report for Flight Delay Intelligence."""
from __future__ import annotations

from app.schemas.delay import DataReadinessReport


class DelayDataReadinessAnalyzer:
    """Analyzes current telemetry against production flight-delay forecasting requirements."""

    @staticmethod
    def get_report() -> DataReadinessReport:
        return DataReadinessReport(
            status="DEMONSTRATION_READY",
            model_type="Deterministic Aviation Scenario Estimator with Airframe Rotation & Atmospheric Linkage",
            current_capabilities=[
                "Airframe rotation tracking across 3,678 flights using tail identifiers (SF0001 - SF0115)",
                "Nearest-airport geospatial origin/destination resolution for ADS-B track trajectories",
                "Spatiotemporal linkage to 2.0° weather grid (precipitation, wind gusts, temperature)",
                "Local airport departure queue estimation within 30-minute rolling windows",
                "Integration with trained RandomForest Congestion Classifier for departure airway metering",
                "En-route segment flight duration prediction via trained RandomForest ETA Regressor",
                "Explicit distinction between scheduled gate departure, estimated pushback, and runway takeoff",
                "Strict evidence categorization: CONFIRMED vs MODEL_INFERRED vs UNAVAILABLE",
            ],
            missing_operational_labels=[
                {
                    "field": "AOBT (Actual Off-Block Time)",
                    "category": "Gate Sensors",
                    "importance": "CRITICAL",
                    "status": "UNAVAILABLE",
                    "reason": "ADS-B telemetry records airborne positions and taxi speeds; physical gate pushback chocks are not broadcast over ADS-B.",
                },
                {
                    "field": "AIBT (Actual In-Block Time)",
                    "category": "Inbound Gate Arrival",
                    "importance": "CRITICAL",
                    "status": "ESTIMATED_VIA_ROTATION",
                    "reason": "Derived from previous track arrival at same airport. Genuine gate docking logs require airport A-CDM integration.",
                },
                {
                    "field": "TSAT / CTOT (Calculated Take-Off Time)",
                    "category": "ATFM Slots",
                    "importance": "HIGH",
                    "status": "SIMULATED_VIA_CONGESTION",
                    "reason": "Air Traffic Flow Management slot allocations require Eurocontrol NM / DGCA CADS operational data feeds.",
                },
                {
                    "field": "Boarding & Baggage Milestones",
                    "category": "Turnaround Sub-processes",
                    "importance": "MEDIUM",
                    "status": "UNAVAILABLE",
                    "reason": "Passenger boarding scanner counts and hold loading reports are internal airline DCS proprietary records.",
                },
            ],
            requirements_for_production=[
                "Ingest historical paired (STD, ATD, STA, ATA) records with at least 50,000 completed commercial flights.",
                "Enforce chronological 70/15/15 train/val/test splits partitioned by departure date to prevent future-to-past target leakage.",
                "Train separate horizon-specific models (Day-Ahead T-24h, Pre-Departure T-4h, Gate-Readiness T-45m).",
                "Validate against historical mean baseline delay to verify statistically significant MAE reduction.",
                "Audit calibration of prediction intervals using pinball loss or conformal prediction intervals.",
            ],
            disclaimer=(
                "Sky Force 2.0 operates a transparent demonstration estimator. It models realistic rotational delay propagation, "
                "departure queue pressure, and convective storm cell impacts, but is explicitly NOT a certified real-world operational delay forecast."
            ),
        )

