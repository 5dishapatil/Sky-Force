"""Versioned prompt templates for the Sky Force Phi-3 Explanation Service."""
from __future__ import annotations

import json
from typing import Any

SYSTEM_PROMPT = """You are the Sky Force Aviation Intelligence Explanation Engine.
Your purpose is to explain verified mathematical computations, machine-learning inferences, and graph-search routing decisions.

CRITICAL OPERATIONAL RULES:
1. Explain ONLY the verified calculations and factual evidence provided in the input context.
2. NEVER invent flight paths, numbers, coordinates, weather conditions, or operational clearances.
3. If weather or congestion data was missing, unobserved, or based on a proxy, explicitly highlight this uncertainty. NEVER claim an unobserved route is hazard-free.
4. Keep explanations clear, rigorous, professional, and suitable for an academic aeronautical engineering panel.
5. Provide a clear summary followed by 3-5 bulleted supporting facts.
"""


def build_route_prompt(context: dict[str, Any], query: str | None = None) -> str:
    path = context.get("path", [])
    objective = context.get("objective", "balanced")
    totals = context.get("totals", {})
    cost_by_factor = context.get("cost_by_factor", {})
    baseline_totals = context.get("baseline_totals", {})
    closed_avoided = context.get("closed_avoided", [])
    provenance = context.get("provenance", {})
    warnings = context.get("warnings", [])

    prompt = f"""Task: Explain why route {' -> '.join(path)} was selected for the '{objective}' objective.

VERIFIED COMPUTATIONAL EVIDENCE:
- Selected Path: {' -> '.join(path)}
- Total Distance: {totals.get('distance_km', 'N/A')} km
- Estimated Traversal Time: {totals.get('estimated_time_min', 'N/A')} min
- Weather Exposure: {totals.get('weather_exposure_km', 0)} severity*km
- Congestion Exposure: {totals.get('congestion_exposure_km', 0)} score*km
- Dimensionless Composite Score: {totals.get('composite_score', 'N/A')}
- Factor Cost Contributions: {json.dumps(cost_by_factor)}

BASELINE COMPARISON (Shortest Distance Path):
- Baseline Distance: {baseline_totals.get('distance_km', 'N/A')} km
- Baseline Time: {baseline_totals.get('estimated_time_min', 'N/A')} min
- Baseline Weather Exposure: {baseline_totals.get('weather_exposure_km', 'N/A')} severity*km
- Baseline Congestion Exposure: {baseline_totals.get('congestion_exposure_km', 'N/A')} score*km

AIRSPACE CONSTRAINTS & PROVENANCE:
- Closed Segments Avoided: {json.dumps(closed_avoided)}
- Data Provenance: {json.dumps(provenance)}
- Operational Warnings: {json.dumps(warnings)}
"""
    if query:
        prompt += f"\nEXAMINER QUESTION TO ANSWER: {query}\n"

    prompt += "\nExplain the trade-offs in distance, time, and hazard exposure that led to this route selection."
    return prompt


def build_quality_prompt(context: dict[str, Any]) -> str:
    return f"""Task: Explain the data quality cleaning and validation audit results.

COMPUTED AUDIT EVIDENCE:
- Input Rows: {context.get('input_rows', 0)}
- Retained Rows: {context.get('retained_rows', 0)}
- Dropped Anomalies: {json.dumps(context.get('dropped', {}))}
- Flagged Plausibility Issues: {json.dumps(context.get('flagged', {}))}
- Missing Field Profile (%): {json.dumps(context.get('missing_profile_pct', {}))}
- Inferred Tracks Formed: {context.get('inferred_tracks', 0)}

Explain why records were flagged or dropped, and what this implies for downstream ML modeling."""

