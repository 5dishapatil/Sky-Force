"""Tests for graph search algorithms (Dijkstra, A*), cost model, and closures."""
from __future__ import annotations

from datetime import datetime, timezone
import pytest

from app.services.routing.context import EdgeAttrs, RoutingContext
from app.services.routing.cost_model import CostWeights
from app.services.routing.graph import RouteGraph, build_graph
from app.services.routing.planner import RoutePlanner


@pytest.fixture
def sample_graph() -> RouteGraph:
    # 4 airports forming a diamond: N0 (origin) -> N1, N2 -> N3 (dest)
    airports = [
        {"node_id": "N0", "name": "Origin", "latitude": 20.0, "longitude": 70.0, "iata": "N0"},
        {"node_id": "N1", "name": "North Branch", "latitude": 22.0, "longitude": 72.0, "iata": "N1"},
        {"node_id": "N2", "name": "South Branch", "latitude": 18.0, "longitude": 72.0, "iata": "N2"},
        {"node_id": "N3", "name": "Destination", "latitude": 20.0, "longitude": 74.0, "iata": "N3"},
    ]
    waypoints: list[dict] = []
    edges = [
        {"edge_id": "N0->N1", "source_node": "N0", "target_node": "N1", "distance_km": 300.0, "bearing_deg": 45.0},
        {"edge_id": "N1->N3", "source_node": "N1", "target_node": "N3", "distance_km": 300.0, "bearing_deg": 135.0},
        {"edge_id": "N0->N2", "source_node": "N0", "target_node": "N2", "distance_km": 320.0, "bearing_deg": 135.0},
        {"edge_id": "N2->N3", "source_node": "N2", "target_node": "N3", "distance_km": 320.0, "bearing_deg": 45.0},
    ]
    return build_graph(airports, waypoints, edges, cruise_kmh=800.0)


def _make_context(rg: RouteGraph) -> RoutingContext:
    edges = {}
    for u, v, d in rg.g.edges(data=True):
        dist = d["distance_km"]
        time_min = dist / (rg.cruise_kmh / 60.0)
        edges[(u, v)] = EdgeAttrs(
            edge_id=d["edge_id"],
            distance_km=dist,
            time_min=time_min,
            time_source="heuristic",
        )
    return RoutingContext(
        scenario_time=datetime.now(timezone.utc),
        scenario_id="test",
        edges=edges,
    )


def test_dijkstra_finds_shortest(sample_graph: RouteGraph):
    planner = RoutePlanner(sample_graph)
    weights = CostWeights.preset("distance")
    ctx = _make_context(sample_graph)
    res = planner.search("N0", "N3", weights, ctx, algorithm="dijkstra")
    assert res.path == ["N0", "N1", "N3"]
    assert res.cost is not None and res.cost > 0.0
    assert res.nodes_expanded > 0


def test_astar_finds_exact_same_optimal_cost(sample_graph: RouteGraph):
    planner = RoutePlanner(sample_graph)
    weights = CostWeights.preset("distance")
    ctx = _make_context(sample_graph)

    d_res = planner.search("N0", "N3", weights, ctx, algorithm="dijkstra")
    a_res = planner.search("N0", "N3", weights, ctx, algorithm="astar")

    assert d_res.path == a_res.path
    assert d_res.cost == pytest.approx(a_res.cost, rel=1e-5)
    # A* expands no more nodes than Dijkstra with an admissible heuristic
    assert a_res.nodes_expanded <= d_res.nodes_expanded


def test_hard_edge_closure(sample_graph: RouteGraph):
    planner = RoutePlanner(sample_graph)
    weights = CostWeights.preset("distance")
    ctx = _make_context(sample_graph)
    # Close N0->N1
    ctx.edges[("N0", "N1")].closed = True

    res = planner.search("N0", "N3", weights, ctx, algorithm="dijkstra")
    # Route must bypass N1 and take N2
    assert res.path == ["N0", "N2", "N3"]


def test_complete_closure_returns_none(sample_graph: RouteGraph):
    planner = RoutePlanner(sample_graph)
    weights = CostWeights.preset("distance")
    ctx = _make_context(sample_graph)
    # Close both N0->N1 and N0->N2
    ctx.edges[("N0", "N1")].closed = True
    ctx.edges[("N0", "N2")].closed = True

    res = planner.search("N0", "N3", weights, ctx, algorithm="dijkstra")
    assert res.path is None
    assert res.cost is None


def test_route_planner_pareto(sample_graph: RouteGraph):
    planner = RoutePlanner(sample_graph)
    ctx = _make_context(sample_graph)
    result = planner.pareto("N0", "N3", ctx)
    assert "routes" in result
    assert result["candidates_evaluated"] >= 1
    assert any(r["non_dominated"] for r in result["routes"])
