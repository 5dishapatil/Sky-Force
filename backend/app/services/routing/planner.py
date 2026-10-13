"""Route planner: primary route, labelled alternatives and non-dominated candidates."""
from __future__ import annotations

import hashlib
import itertools
from typing import Any

import networkx as nx

from app.core.errors import ValidationFailed
from app.services.geospatial.geo import haversine_km
from app.services.routing.context import RoutingContext
from app.services.routing.cost_model import FACTORS, OBJECTIVE_PRESETS, CostModel, CostWeights
from app.services.routing.graph import RouteGraph
from app.services.routing.search import SearchResult, astar, dijkstra

ALT_LABELS = ["distance", "fastest", "weather", "congestion", "balanced"]
OBJECTIVE_NAMES = {
    "distance": "Shortest-distance baseline", "fastest": "Fastest candidate", "weather": "Weather-aware",
    "congestion": "Congestion-aware", "balanced": "Composite balanced", "custom": "Custom weights",
}


def route_id(path: list[str]) -> str:
    return "R-" + hashlib.sha1("|".join(path).encode()).hexdigest()[:8]


class RoutePlanner:
    def __init__(self, rg: RouteGraph):
        self.rg = rg
        self.cm = CostModel(rg.ref_km, rg.ref_min)

    # ------------------------------------------------------------------ search
    def validate_od(self, origin: str, destination: str) -> None:
        unknown = [n for n in (origin, destination) if not self.rg.has_node(n)]
        if unknown:
            raise ValidationFailed(f"Unknown node(s): {', '.join(unknown)}", code="UNKNOWN_NODE",
                                   details={"unknown": unknown})
        if origin == destination:
            raise ValidationFailed("Origin and destination must differ", code="SAME_ORIGIN_DESTINATION")

    def search(self, origin: str, destination: str, w: CostWeights, ctx: RoutingContext, algorithm: str,
               respect_closures: bool = True) -> SearchResult:
        def cost_fn(u: str, v: str) -> float | None:
            a = ctx.edges[(u, v)]
            if respect_closures and a.closed:
                return None
            return self.cm.edge_cost(a, w)

        if algorithm == "dijkstra":
            return dijkstra(self.rg.g, origin, destination, cost_fn)
        if algorithm == "astar":
            coef = self.cm.heuristic_coefficient(w, ctx.v_max_km_per_min)
            goal = self.rg.pos(destination)
            return astar(self.rg.g, origin, destination, cost_fn, lambda n: coef * haversine_km(*self.rg.pos(n), *goal))
        raise ValidationFailed(f"Unknown algorithm '{algorithm}'", details={"allowed": ["dijkstra", "astar"]})

    # --------------------------------------------------------------- evaluate
    def evaluate(self, path: list[str], ctx: RoutingContext, w: CostWeights) -> dict[str, Any]:
        segs = []
        tot = {k: 0.0 for k in FACTORS}
        geometry: list[list[float]] = []
        d_km = t_min = wx_exp = cg_exp = unc_km = 0.0
        closed_in_route = 0
        time_sources, weather_sources, cong_sources, flags = set(), set(), set(), set()
        for u, v in zip(path[:-1], path[1:]):
            a = ctx.edges[(u, v)]
            comps = self.cm.components(a)
            weighted = self.cm.weighted(comps, w)
            for k in FACTORS:
                tot[k] += weighted[k]
            d_km += a.distance_km
            t_min += a.time_min
            wx_exp += (a.weather_severity or 0) * a.distance_km
            cg_exp += (a.congestion_score or 0) * a.distance_km
            unc_km += a.uncertainty * a.distance_km
            closed_in_route += int(a.closed)
            time_sources.add(a.time_source)
            weather_sources.add(a.weather_source)
            cong_sources.add(a.congestion_source)
            flags.update(a.flags)
            geom = self.rg.edge_geometry(u, v)
            geometry.extend([list(p) for p in (geom if not geometry else geom[1:])])
            segs.append({
                "edge_id": a.edge_id, "from_node": u, "to_node": v, "distance_km": round(a.distance_km, 2),
                "time_min": round(a.time_min, 2), "time_source": a.time_source,
                "weather_severity": None if a.weather_severity is None else round(a.weather_severity, 3),
                "weather_source": a.weather_source,
                "congestion_score": None if a.congestion_score is None else round(a.congestion_score, 3),
                "congestion_class": a.congestion_class, "congestion_probs": a.congestion_probs,
                "congestion_source": a.congestion_source, "uncertainty": round(a.uncertainty, 3),
                "closed": a.closed, "closure_reasons": a.closure_reasons, "event_ids": a.event_ids, "flags": a.flags,
                "cost_components": {k: round(comps[k], 4) for k in FACTORS},
                "weighted_cost": {k: round(weighted[k], 4) for k in FACTORS},
                "cost_total": round(sum(weighted.values()), 4),
            })
        composite = sum(tot.values())
        return {
            "route_id": route_id(path), "path": path, "geometry": geometry, "segments": segs,
            "totals": {
                "distance_km": round(d_km, 1), "estimated_time_min": round(t_min, 1),
                "weather_exposure_km": round(wx_exp, 1), "congestion_exposure_km": round(cg_exp, 1),
                "mean_uncertainty": round(unc_km / d_km, 3) if d_km else 0.0,
                "composite_score": round(composite, 4), "hops": len(path) - 1,
                "closed_edges_in_route": closed_in_route,
            },
            "cost_by_factor": {k: round(tot[k], 4) for k in FACTORS},
            "provenance": {"time": sorted(time_sources), "weather": sorted(weather_sources),
                           "congestion": sorted(cong_sources), "flags": sorted(flags)},
        }

    # ------------------------------------------------------------ public API
    def plan(self, origin: str, destination: str, w: CostWeights, ctx: RoutingContext, algorithm: str,
             label: str = "selected") -> dict[str, Any]:
        self.validate_od(origin, destination)
        res = self.search(origin, destination, w, ctx, algorithm)
        if res.path is None:
            return {"found": False, "label": label, "algorithm": algorithm, "weights": w.as_dict(),
                    "search": {"nodes_expanded": res.nodes_expanded, "latency_ms": round(res.latency_ms, 3)},
                    "reason": self._no_route_reason(origin, destination, ctx)}
        out = self.evaluate(res.path, ctx, w)
        out.update({"found": True, "label": label, "algorithm": algorithm, "weights": w.as_dict(),
                    "search": {"nodes_expanded": res.nodes_expanded, "latency_ms": round(res.latency_ms, 3),
                               "search_cost": round(res.cost or 0, 4)}})
        return out

    def _no_route_reason(self, origin: str, destination: str, ctx: RoutingContext) -> str:
        if not nx.has_path(self.rg.g, origin, destination):
            return "The graph has no directed connection between origin and destination."
        n_closed = sum(a.closed for a in ctx.edges.values())
        return (f"All connecting paths are blocked by {n_closed} closed segment(s) under the active scenario. "
                "Closures are hard constraints; no route was fabricated.")

    def alternatives(self, origin: str, destination: str, selected_w: CostWeights, objective: str,
                     ctx: RoutingContext, algorithm: str) -> list[dict[str, Any]]:
        variants = [(objective, selected_w)] + [(lbl, CostWeights.preset(lbl)) for lbl in ALT_LABELS if lbl != objective]
        routes: dict[str, dict] = {}
        order = []
        for lbl, w in variants:
            r = self.plan(origin, destination, w, ctx, algorithm, label=lbl)
            if not r["found"]:
                continue
            r["score_under_selected"] = round(sum(self.evaluate(r["path"], ctx, selected_w)["cost_by_factor"].values()), 4)
            rid = r["route_id"]
            if rid in routes:
                routes[rid]["labels"].append(lbl)
            else:
                r["labels"] = [lbl]
                routes[rid] = r
                order.append(rid)
        out = [routes[rid] for rid in order]
        for r in out:
            r["label_names"] = [OBJECTIVE_NAMES.get(lbl, lbl) for lbl in r["labels"]]
        return out

    def pareto(self, origin: str, destination: str, ctx: RoutingContext, algorithm: str = "dijkstra",
               k_shortest: int = 8) -> dict[str, Any]:
        """Non-dominated candidates among (a) a weighted-sum sweep and (b) Yen's k-shortest paths.

        Objectives (all minimised): distance_km, estimated_time_min, weather_exposure_km, congestion_exposure_km.
        Supported (convex-hull) points are found by the sweep; Yen's paths add some non-supported ones.
        This is NOT an exhaustive multi-objective label-setting search.
        """
        self.validate_od(origin, destination)
        paths: dict[str, list[str]] = {}
        steps = [0.0, 0.5, 1.0]
        for wd, wt, ww, wc in itertools.product(steps, repeat=4):
            if wd + wt + ww + wc == 0:
                continue
            w = CostWeights.from_dict({"distance": wd, "time": wt, "weather": ww, "congestion": wc})
            r = self.search(origin, destination, w, ctx, algorithm)
            if r.path:
                paths[route_id(r.path)] = r.path
        open_g = nx.DiGraph()
        bal = CostWeights.preset("balanced")
        for (u, v), a in ctx.edges.items():
            if not a.closed:
                open_g.add_edge(u, v, w=self.cm.edge_cost(a, bal))
        if open_g.has_node(origin) and open_g.has_node(destination) and nx.has_path(open_g, origin, destination):
            for p in itertools.islice(nx.shortest_simple_paths(open_g, origin, destination, weight="w"), k_shortest):
                paths[route_id(p)] = p
        evaluated = [self.evaluate(p, ctx, bal) for p in paths.values()]
        keys = ["distance_km", "estimated_time_min", "weather_exposure_km", "congestion_exposure_km"]
        vecs = [[e["totals"][k] for k in keys] for e in evaluated]
        for i, e in enumerate(evaluated):
            dominated = any(all(vecs[j][m] <= vecs[i][m] for m in range(4)) and any(vecs[j][m] < vecs[i][m] for m in range(4))
                            for j in range(len(vecs)) if j != i)
            e["non_dominated"] = not dominated
        evaluated.sort(key=lambda e: (not e["non_dominated"], e["totals"]["distance_km"]))
        return {"objectives": keys, "candidates_evaluated": len(evaluated),
                "routes": evaluated,
                "method": "weighted-sum sweep (3^4 grid) + Yen k-shortest (balanced cost); dominance filter on evaluated set",
                "caveat": "Non-dominated among the evaluated candidate set only; not a guaranteed complete Pareto front."}


def closed_edges_on_unconstrained(planner: RoutePlanner, origin: str, destination: str, ctx: RoutingContext,
                                  w: CostWeights, algorithm: str) -> list[dict[str, Any]]:
    """Closed edges lying on the route that WOULD be chosen if closures were ignored."""
    r = planner.search(origin, destination, w, ctx, algorithm, respect_closures=False)
    if not r.path:
        return []
    out = []
    for u, v in zip(r.path[:-1], r.path[1:]):
        a = ctx.edges[(u, v)]
        if a.closed:
            out.append({"edge_id": a.edge_id, "reasons": a.closure_reasons})
    return out


__all__ = ["RoutePlanner", "closed_edges_on_unconstrained", "OBJECTIVE_PRESETS", "OBJECTIVE_NAMES"]
