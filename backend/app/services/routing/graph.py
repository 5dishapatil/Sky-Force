"""Directed research route graph.

Nodes: airports (OurAirports coordinates) and synthetic research-only waypoints.
Edges: synthetic candidate segments - NOT approved airways. Edge length is the
haversine great-circle distance between its end nodes.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import numpy as np

from app.services.geospatial.geo import sample_segment


@dataclass
class RouteGraph:
    g: nx.DiGraph
    ref_km: float          # median edge length (normalisation reference)
    ref_min: float         # median heuristic edge time (normalisation reference)
    cruise_kmh: float
    _geom_cache: dict = field(default_factory=dict)

    def has_node(self, n: str) -> bool:
        return n in self.g

    def pos(self, n: str) -> tuple[float, float]:
        d = self.g.nodes[n]
        return d["lat"], d["lon"]

    def edge(self, u: str, v: str) -> dict:
        return self.g.edges[u, v]

    def edge_geometry(self, u: str, v: str, step_km: float = 40.0) -> list[tuple[float, float]]:
        key = (u, v, step_km)
        if key not in self._geom_cache:
            self._geom_cache[key] = sample_segment(*self.pos(u), *self.pos(v), step_km)
        return self._geom_cache[key]

    @property
    def edge_ids(self) -> dict[str, tuple[str, str]]:
        return {d["edge_id"]: (u, v) for u, v, d in self.g.edges(data=True)}


def build_graph(airports: list[dict], waypoints: list[dict], edges: list[dict], cruise_kmh: float) -> RouteGraph:
    g = nx.DiGraph()
    for a in airports:
        g.add_node(a["node_id"], lat=a["latitude"], lon=a["longitude"], kind="airport", name=a["name"],
                   iata=a.get("iata"), source=a.get("source"))
    for w in waypoints:
        g.add_node(w["node_id"], lat=w["latitude"], lon=w["longitude"], kind="waypoint", name=w["name"],
                   source=w.get("source"))
    for e in edges:
        if e["source_node"] not in g or e["target_node"] not in g:
            continue
        g.add_edge(e["source_node"], e["target_node"], edge_id=e["edge_id"], distance_km=float(e["distance_km"]),
                   bearing_deg=float(e["bearing_deg"]), is_synthetic=bool(e.get("is_synthetic", True)),
                   provenance=e.get("provenance", ""))
    dists = np.array([d["distance_km"] for _, _, d in g.edges(data=True)]) if g.number_of_edges() else np.array([1.0])
    ref_km = float(np.median(dists))
    return RouteGraph(g=g, ref_km=ref_km, ref_min=ref_km / cruise_kmh * 60.0, cruise_kmh=cruise_kmh)
