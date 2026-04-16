"""Dependency graph analysis service — graph algorithms using only stdlib."""

import logging
from collections import defaultdict, deque

from app.schemas.dependency import (
    DependencyEdge,
    DependencyGraph,
    WorkloadSummary,
)

logger = logging.getLogger(__name__)


class DependencyAnalyzer:
    """Builds and analyzes workload dependency graphs."""

    def get_dependency_graph(
        self, workloads: list[WorkloadSummary], edges: list[DependencyEdge] | None = None
    ) -> DependencyGraph:
        """Build and analyse a dependency graph.

        Args:
            workloads: Flat list of workload summaries to use as graph nodes.
            edges: Explicit list of directed edges.  When *None* (or an empty
                list) the graph contains nodes only and no edges — callers are
                responsible for building edges from workload data before
                calling this method (see ``_workloads_to_graph`` in
                ``app.api.routes.workloads``).

        Returns:
            A :class:`DependencyGraph` with nodes, edges, detected circular
            dependencies, and migration groups already populated.
        """
        if edges is None:
            edges = []

        graph = DependencyGraph(
            nodes=list(workloads),
            edges=list(edges),
        )

        circular = self.find_circular_dependencies(graph)
        groups = self.find_migration_groups(graph)
        graph.circular_dependencies = circular
        graph.migration_groups = groups
        return graph

    # ------------------------------------------------------------------
    # Graph algorithm helpers
    # ------------------------------------------------------------------

    def _build_adjacency(
        self, graph: DependencyGraph
    ) -> tuple[dict[str, list[str]], set[str]]:
        """Return (adjacency_list, all_node_ids)."""
        node_ids = {n.id for n in graph.nodes}
        adj: dict[str, list[str]] = defaultdict(list)
        for edge in graph.edges:
            if edge.source in node_ids and edge.target in node_ids:
                adj[edge.source].append(edge.target)
        return dict(adj), node_ids

    def find_circular_dependencies(self, graph: DependencyGraph) -> list[list[str]]:
        """Return a list of cycles using DFS (Johnson's algorithm simplified).

        Each cycle is represented as an ordered list of workload IDs.
        """
        adj, node_ids = self._build_adjacency(graph)
        cycles: list[list[str]] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> None:
            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbour in adj.get(node, []):
                if neighbour not in visited:
                    dfs(neighbour)
                elif neighbour in rec_stack:
                    # Found a cycle — extract the loop portion
                    idx = path.index(neighbour)
                    cycle = path[idx:]
                    # Normalise: start from the smallest ID to deduplicate
                    min_idx = cycle.index(min(cycle))
                    normalised = cycle[min_idx:] + cycle[:min_idx]
                    if normalised not in cycles:
                        cycles.append(normalised)

            path.pop()
            rec_stack.discard(node)

        for node in sorted(node_ids):
            if node not in visited:
                dfs(node)

        logger.debug("Found %d circular dependency cycle(s)", len(cycles))
        return cycles

    def find_migration_groups(self, graph: DependencyGraph) -> list[list[str]]:
        """Return connected components (undirected) that must move together."""
        node_ids = {n.id for n in graph.nodes}
        # Build undirected adjacency
        neighbours: dict[str, set[str]] = {nid: set() for nid in node_ids}
        for edge in graph.edges:
            if edge.source in node_ids and edge.target in node_ids:
                neighbours[edge.source].add(edge.target)
                neighbours[edge.target].add(edge.source)

        visited: set[str] = set()
        groups: list[list[str]] = []

        for start in sorted(node_ids):
            if start in visited:
                continue
            # BFS
            component: list[str] = []
            queue: deque[str] = deque([start])
            visited.add(start)
            while queue:
                current = queue.popleft()
                component.append(current)
                for nb in sorted(neighbours.get(current, set())):
                    if nb not in visited:
                        visited.add(nb)
                        queue.append(nb)
            groups.append(sorted(component))

        logger.debug("Found %d migration group(s)", len(groups))
        return groups

    def suggest_migration_order(self, graph: DependencyGraph) -> list[str]:
        """Return a topological ordering (Kahn's algorithm).

        Edge convention: ``source → target`` means *source is a prerequisite
        for target* — source appears before target in the returned order.

        Raises ``ValueError`` if the graph contains circular dependencies.
        """
        cycles = self.find_circular_dependencies(graph)
        if cycles:
            cycle_ids = [" -> ".join(c) for c in cycles]
            raise ValueError(
                "Cannot suggest migration order: circular dependencies detected: "
                + "; ".join(cycle_ids)
            )

        adj, node_ids = self._build_adjacency(graph)

        # Compute in-degrees
        in_degree: dict[str, int] = {nid: 0 for nid in node_ids}
        for node in node_ids:
            for neighbour in adj.get(node, []):
                in_degree[neighbour] = in_degree.get(neighbour, 0) + 1

        # Initialise queue with zero-in-degree nodes (sorted for determinism)
        queue: deque[str] = deque(sorted(n for n, d in in_degree.items() if d == 0))
        order: list[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbour in sorted(adj.get(node, [])):
                in_degree[neighbour] -= 1
                if in_degree[neighbour] == 0:
                    queue.append(neighbour)

        logger.debug("Topological order has %d nodes", len(order))
        return order
