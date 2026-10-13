"""Human-readable route explanations computed from the actual route and edge attributes."""
from __future__ import annotations

from typing import Any

from app.services.routing.context import RoutingContext

FACTOR_LABEL = {"distance": "distance", "time": "estimated time", "weather": "weather exposure",
                "congestion": "congestion penalty", "uncertainty": "data-uncertainty penalty"}


def _fmt_pct(a: float, b: float) -> str:
    return f"{(a - b) / b * 100:+.1f}%" if b else "n/a"


def explain_route(route: dict[str, Any], baseline: dict[str, Any] | None, ctx: RoutingContext, objective_name: str,
                  closed_on_direct: list[dict[str, Any]]) -> list[str]:
    if not route.get("found"):
        return [route.get("reason", "No route found."),
                "Research estimate only - not an operational clearance."]
    t = route["totals"]
    lines = [
        f"Route {' → '.join(route['path'])} ranks first for the '{objective_name}' objective "
        f"({t['hops']} segments, {t['distance_km']:.0f} km, ~{t['estimated_time_min']:.0f} min)."
    ]
    if baseline and baseline.get("found"):
        b = baseline["totals"]
        if baseline["route_id"] == route["route_id"]:
            lines.append("It coincides with the shortest-distance candidate under the current conditions.")
        else:
            dd = t["distance_km"] - b["distance_km"]
            lines.append(
                f"Compared with the shortest-distance candidate it is {abs(dd):.0f} km {'longer' if dd > 0 else 'shorter'} "
                f"({_fmt_pct(t['distance_km'], b['distance_km'])}); estimated time {t['estimated_time_min'] - b['estimated_time_min']:+.1f} min, "
                f"weather exposure {t['weather_exposure_km'] - b['weather_exposure_km']:+.0f} severity·km, "
                f"congestion exposure {t['congestion_exposure_km'] - b['congestion_exposure_km']:+.0f} score·km.")
    cbf = route["cost_by_factor"]
    total = sum(cbf.values())
    if total > 0:
        top = max(cbf, key=cbf.get)
        lines.append(f"The largest share of its composite score comes from {FACTOR_LABEL[top]} ({cbf[top] / total * 100:.0f}%).")
    if closed_on_direct:
        ids = ", ".join(c["edge_id"] for c in closed_on_direct)
        reasons = sorted({r for c in closed_on_direct for r in c["reasons"]})
        lines.append(f"{len(closed_on_direct)} segment(s) on the otherwise-preferred path are closed ({ids}) and were excluded "
                     f"as hard constraints. Reason: {'; '.join(reasons)}.")
    evented = [s for s in route["segments"] if s["event_ids"]]
    if evented:
        lines.append(f"{len(evented)} segment(s) on this route are affected by simulated events "
                     f"({', '.join(sorted({e for s in evented for e in s['event_ids']}))}).")
    prov = route["provenance"]
    lines.append(f"Estimated time source: {'; '.join(prov['time'])}.")
    lines.append(f"Weather source: {'; '.join(prov['weather'])}.")
    lines.append(f"Congestion source: {'; '.join(prov['congestion'])}.")
    unc = [s for s in route["segments"] if s["uncertainty"] >= 0.4]
    if unc:
        lines.append(f"Caution: {len(unc)} segment(s) have elevated data uncertainty (missing, stale or low-confidence inputs).")
    lines.append("This is a research estimate on a synthetic candidate network, not an operational clearance.")
    return lines
