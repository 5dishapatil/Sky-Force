"""Dijkstra and A* (implemented explicitly so node expansions can be measured).

Complexity: O((V + E) log V) with a binary heap. Edge costs must be > 0
(enforced by CostModel). ``cost_fn`` returns ``None`` for an excluded (closed)
edge - closures are hard constraints. The results are validated against
NetworkX's reference implementation in the test-suite.
"""
from __future__ import annotations

import heapq
import itertools
import time
from collections.abc import Callable
from dataclasses import dataclass

import networkx as nx

CostFn = Callable[[str, str], float | None]
HeurFn = Callable[[str], float]


@dataclass
class SearchResult:
    path: list[str] | None
    cost: float | None
    nodes_expanded: int
    latency_ms: float
    algorithm: str


def _reconstruct(prev: dict[str, str], src: str, dst: str) -> list[str]:
    path = [dst]
    while path[-1] != src:
        path.append(prev[path[-1]])
    return path[::-1]


def best_first(g: nx.DiGraph, src: str, dst: str, cost_fn: CostFn, h: HeurFn | None = None,
               algorithm: str = "dijkstra") -> SearchResult:
    t0 = time.perf_counter()
    h = h or (lambda _n: 0.0)
    counter = itertools.count()
    dist = {src: 0.0}
    prev: dict[str, str] = {}
    closed: set[str] = set()
    heap = [(h(src), next(counter), src)]
    expanded = 0
    while heap:
        _, _, u = heapq.heappop(heap)
        if u in closed:
            continue
        closed.add(u)
        expanded += 1
        if u == dst:
            return SearchResult(_reconstruct(prev, src, dst), dist[u], expanded, (time.perf_counter() - t0) * 1000, algorithm)
        for v in g.successors(u):
            if v in closed:
                continue
            c = cost_fn(u, v)
            if c is None:
                continue
            nd = dist[u] + c
            if nd < dist.get(v, float("inf")):
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd + h(v), next(counter), v))
    return SearchResult(None, None, expanded, (time.perf_counter() - t0) * 1000, algorithm)


def dijkstra(g: nx.DiGraph, src: str, dst: str, cost_fn: CostFn) -> SearchResult:
    return best_first(g, src, dst, cost_fn, None, "dijkstra")


def astar(g: nx.DiGraph, src: str, dst: str, cost_fn: CostFn, h: HeurFn) -> SearchResult:
    """A* with a consistent heuristic (see CostModel.heuristic_coefficient) -> optimal path."""
    return best_first(g, src, dst, cost_fn, h, "astar")
