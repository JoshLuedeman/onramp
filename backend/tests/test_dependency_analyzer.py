"""Tests for the DependencyAnalyzer service."""

import pytest

from app.schemas.dependency import DependencyEdge, DependencyGraph, WorkloadSummary
from app.services.dependency_analyzer import DependencyAnalyzer


@pytest.fixture
def analyzer():
    return DependencyAnalyzer()


def _workload(wid: str, name: str = "") -> WorkloadSummary:
    """Helper to create a minimal WorkloadSummary."""
    return WorkloadSummary(
        id=wid,
        name=name or wid,
        criticality="medium",
        migration_strategy="rehost",
        project_id="test-project",
    )


def _edge(src: str, tgt: str) -> DependencyEdge:
    return DependencyEdge(source=src, target=tgt)


# ---------------------------------------------------------------------------
# get_dependency_graph
# ---------------------------------------------------------------------------


class TestGetDependencyGraph:
    def test_empty_graph(self, analyzer: DependencyAnalyzer):
        graph = analyzer.get_dependency_graph(workloads=[], edges=[])
        assert graph.nodes == []
        assert graph.edges == []
        assert graph.circular_dependencies == []
        assert graph.migration_groups == []

    def test_nodes_only_no_edges(self, analyzer: DependencyAnalyzer):
        workloads = [_workload("a"), _workload("b"), _workload("c")]
        graph = analyzer.get_dependency_graph(workloads=workloads)
        assert len(graph.nodes) == 3
        assert graph.edges == []
        # Each node is its own migration group
        assert len(graph.migration_groups) == 3

    def test_simple_chain(self, analyzer: DependencyAnalyzer):
        workloads = [_workload("a"), _workload("b"), _workload("c")]
        edges = [_edge("a", "b"), _edge("b", "c")]
        graph = analyzer.get_dependency_graph(workloads=workloads, edges=edges)
        assert len(graph.edges) == 2
        assert graph.circular_dependencies == []
        # All connected → 1 migration group
        assert len(graph.migration_groups) == 1

    def test_detects_circular_dependency(self, analyzer: DependencyAnalyzer):
        workloads = [_workload("a"), _workload("b")]
        edges = [_edge("a", "b"), _edge("b", "a")]
        graph = analyzer.get_dependency_graph(workloads=workloads, edges=edges)
        assert len(graph.circular_dependencies) >= 1


# ---------------------------------------------------------------------------
# find_circular_dependencies
# ---------------------------------------------------------------------------


class TestFindCircularDependencies:
    def test_no_cycles(self, analyzer: DependencyAnalyzer):
        graph = DependencyGraph(
            nodes=[_workload("a"), _workload("b"), _workload("c")],
            edges=[_edge("a", "b"), _edge("b", "c")],
        )
        cycles = analyzer.find_circular_dependencies(graph)
        assert cycles == []

    def test_simple_cycle(self, analyzer: DependencyAnalyzer):
        graph = DependencyGraph(
            nodes=[_workload("a"), _workload("b")],
            edges=[_edge("a", "b"), _edge("b", "a")],
        )
        cycles = analyzer.find_circular_dependencies(graph)
        assert len(cycles) == 1
        assert set(cycles[0]) == {"a", "b"}

    def test_three_node_cycle(self, analyzer: DependencyAnalyzer):
        graph = DependencyGraph(
            nodes=[_workload("a"), _workload("b"), _workload("c")],
            edges=[_edge("a", "b"), _edge("b", "c"), _edge("c", "a")],
        )
        cycles = analyzer.find_circular_dependencies(graph)
        assert len(cycles) == 1
        assert set(cycles[0]) == {"a", "b", "c"}

    def test_isolated_nodes_no_cycles(self, analyzer: DependencyAnalyzer):
        graph = DependencyGraph(
            nodes=[_workload("a"), _workload("b")],
            edges=[],
        )
        cycles = analyzer.find_circular_dependencies(graph)
        assert cycles == []


# ---------------------------------------------------------------------------
# find_migration_groups
# ---------------------------------------------------------------------------


class TestFindMigrationGroups:
    def test_single_component(self, analyzer: DependencyAnalyzer):
        graph = DependencyGraph(
            nodes=[_workload("a"), _workload("b")],
            edges=[_edge("a", "b")],
        )
        groups = analyzer.find_migration_groups(graph)
        assert len(groups) == 1
        assert sorted(groups[0]) == ["a", "b"]

    def test_two_components(self, analyzer: DependencyAnalyzer):
        graph = DependencyGraph(
            nodes=[_workload("a"), _workload("b"), _workload("c"), _workload("d")],
            edges=[_edge("a", "b"), _edge("c", "d")],
        )
        groups = analyzer.find_migration_groups(graph)
        assert len(groups) == 2

    def test_all_isolated(self, analyzer: DependencyAnalyzer):
        graph = DependencyGraph(
            nodes=[_workload("x"), _workload("y"), _workload("z")],
            edges=[],
        )
        groups = analyzer.find_migration_groups(graph)
        assert len(groups) == 3


# ---------------------------------------------------------------------------
# suggest_migration_order
# ---------------------------------------------------------------------------


class TestSuggestMigrationOrder:
    def test_simple_chain_order(self, analyzer: DependencyAnalyzer):
        graph = DependencyGraph(
            nodes=[_workload("a"), _workload("b"), _workload("c")],
            edges=[_edge("a", "b"), _edge("b", "c")],
        )
        order = analyzer.suggest_migration_order(graph)
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_diamond_graph(self, analyzer: DependencyAnalyzer):
        graph = DependencyGraph(
            nodes=[_workload("a"), _workload("b"), _workload("c"), _workload("d")],
            edges=[_edge("a", "b"), _edge("a", "c"), _edge("b", "d"), _edge("c", "d")],
        )
        order = analyzer.suggest_migration_order(graph)
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")

    def test_raises_on_cycle(self, analyzer: DependencyAnalyzer):
        graph = DependencyGraph(
            nodes=[_workload("a"), _workload("b")],
            edges=[_edge("a", "b"), _edge("b", "a")],
        )
        with pytest.raises(ValueError, match="circular dependencies"):
            analyzer.suggest_migration_order(graph)

    def test_no_edges_returns_all_nodes(self, analyzer: DependencyAnalyzer):
        graph = DependencyGraph(
            nodes=[_workload("a"), _workload("b")],
            edges=[],
        )
        order = analyzer.suggest_migration_order(graph)
        assert set(order) == {"a", "b"}
