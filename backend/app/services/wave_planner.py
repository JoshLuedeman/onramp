"""Migration wave planning service."""

import csv
import io
import logging
from collections import defaultdict

from app.schemas.dependency import DependencyEdge, WorkloadSummary

logger = logging.getLogger(__name__)

COMPLEXITY_SCORES: dict[str, int] = {
    "rehost": 1,
    "refactor": 2,
    "rearchitect": 3,
    "rebuild": 4,
    "replace": 5,
    "unknown": 3,
}

CRITICALITY_ORDER_SAFE: dict[str, int] = {
    "dev-test": 0,
    "standard": 1,
    "business-critical": 2,
    "mission-critical": 3,
}

CRITICALITY_ORDER_PRIORITY: dict[str, int] = {
    "mission-critical": 0,
    "business-critical": 1,
    "standard": 2,
    "dev-test": 3,
}


class WavePlanner:
    """Groups workloads into migration waves."""

    @staticmethod
    def _find_cycles(
        nodes: set[str],
        edges: list[DependencyEdge],
    ) -> list[list[str]]:
        """Detect circular dependencies using iterative DFS.

        Returns a list of cycles, each a list of node IDs.
        """
        adj: dict[str, list[str]] = defaultdict(list)
        for edge in edges:
            if edge.source in nodes and edge.target in nodes:
                adj[edge.source].append(edge.target)

        visited: set[str] = set()
        in_stack: set[str] = set()
        cycles: list[list[str]] = []

        for start in sorted(nodes):
            if start in visited:
                continue
            # Iterative DFS with explicit stack
            stack: list[tuple[str, int]] = [(start, 0)]
            path: list[str] = []
            while stack:
                node, idx = stack.pop()
                # If we're backtracking
                if idx == 0:
                    if node in visited and node not in in_stack:
                        continue
                    if node in in_stack:
                        # Found a cycle
                        if node in path:
                            cycle_start = path.index(node)
                            cycles.append(path[cycle_start:] + [node])
                        continue
                    visited.add(node)
                    in_stack.add(node)
                    path.append(node)
                neighbors = adj.get(node, [])
                if idx < len(neighbors):
                    # Push current node back with next index
                    stack.append((node, idx + 1))
                    # Push neighbor
                    stack.append((neighbors[idx], 0))
                else:
                    # Done with this node
                    in_stack.discard(node)
                    if path and path[-1] == node:
                        path.pop()

        return cycles

    def generate_waves(
        self,
        workloads: list[WorkloadSummary],
        edges: list[DependencyEdge] | None = None,
        strategy: str = "complexity_first",
        max_wave_size: int | None = None,
    ) -> list[list[WorkloadSummary]]:
        """Generate migration waves from workloads and dependencies.

        Args:
            workloads: List of workload summaries.
            edges: Dependency edges.  If None, uses empty list.
            strategy: "complexity_first" (simple first) or
                "priority_first" (critical first).
            max_wave_size: Max workloads per wave.  None = unlimited.

        Returns:
            List of waves, each a list of WorkloadSummary objects.
        """
        if not workloads:
            return []

        edges = edges or []
        workload_map = {w.id: w for w in workloads}

        # Detect cycles using built-in DFS
        all_ids = {w.id for w in workloads}
        cycles = self._find_cycles(all_ids, edges)
        cycle_nodes: set[str] = set()
        for cycle in cycles:
            cycle_nodes.update(cycle)

        # Get topological layers (respecting dependencies)
        layers = self._topological_layers(workloads, edges, cycle_nodes)

        # Sort within each layer by strategy
        criticality_order = (
            CRITICALITY_ORDER_PRIORITY
            if strategy == "priority_first"
            else CRITICALITY_ORDER_SAFE
        )

        for layer in layers:
            layer.sort(
                key=lambda wid: (
                    criticality_order.get(
                        workload_map[wid].criticality, 2
                    ),
                    COMPLEXITY_SCORES.get(
                        workload_map[wid].migration_strategy, 3
                    ),
                    workload_map[wid].name,
                )
            )

        # Split into waves respecting max_wave_size
        waves: list[list[WorkloadSummary]] = []
        for layer in layers:
            layer_workloads = [
                workload_map[wid]
                for wid in layer
                if wid in workload_map
            ]
            if not layer_workloads:
                continue
            if max_wave_size and len(layer_workloads) > max_wave_size:
                for i in range(0, len(layer_workloads), max_wave_size):
                    chunk = layer_workloads[i : i + max_wave_size]
                    if chunk:
                        waves.append(chunk)
            else:
                waves.append(layer_workloads)

        return waves

    def _topological_layers(
        self,
        workloads: list[WorkloadSummary],
        edges: list[DependencyEdge],
        cycle_nodes: set[str],
    ) -> list[list[str]]:
        """Compute topological layers using Kahn's algorithm variant.

        Each layer contains workloads whose dependencies are all in
        earlier layers.  Cyclic workloads are placed together in their
        own layer at the end.

        Args:
            workloads: All workloads.
            edges: Dependency edges (source is prerequisite of target).
            cycle_nodes: IDs of workloads involved in cycles.

        Returns:
            List of layers, each a list of workload IDs.
        """
        all_ids = {w.id for w in workloads}
        non_cycle_ids = all_ids - cycle_nodes

        # Build adjacency for non-cycle nodes only
        in_degree: dict[str, int] = {wid: 0 for wid in non_cycle_ids}
        dependents: dict[str, list[str]] = {wid: [] for wid in non_cycle_ids}

        for edge in edges:
            if edge.source in non_cycle_ids and edge.target in non_cycle_ids:
                in_degree[edge.target] = in_degree.get(edge.target, 0) + 1
                dependents.setdefault(edge.source, []).append(edge.target)

        layers: list[list[str]] = []

        # Process non-cycle nodes in topological layers
        current_layer = [
            wid for wid in non_cycle_ids if in_degree.get(wid, 0) == 0
        ]
        while current_layer:
            layers.append(sorted(current_layer))
            next_layer: list[str] = []
            for wid in current_layer:
                for dep in dependents.get(wid, []):
                    in_degree[dep] -= 1
                    if in_degree[dep] == 0:
                        next_layer.append(dep)
            current_layer = next_layer

        # Add cycle nodes as a separate layer at the end
        if cycle_nodes:
            layers.append(sorted(cycle_nodes))

        return layers

    def validate_waves(
        self,
        waves: list[dict],
        workload_map: dict[str, WorkloadSummary],
        edges: list[DependencyEdge],
        max_wave_size: int | None = None,
    ) -> list[dict]:
        """Validate a wave plan for dependency violations and sizing.

        Args:
            waves: List of wave dicts with "id", "order", "workload_ids".
            workload_map: Map of workload_id to WorkloadSummary.
            edges: Dependency edges.
            max_wave_size: Optional max workloads per wave.

        Returns:
            List of warning dicts.
        """
        warnings: list[dict] = []

        # Build wave assignment map: workload_id -> wave_order
        wave_assignment: dict[str, int] = {}
        for wave in waves:
            for wid in wave.get("workload_ids", []):
                wave_assignment[wid] = wave["order"]

        # Check dependency violations
        for edge in edges:
            source_wave = wave_assignment.get(edge.source)
            target_wave = wave_assignment.get(edge.target)
            if source_wave is not None and target_wave is not None:
                if source_wave > target_wave:
                    source_name = workload_map.get(edge.source)
                    target_name = workload_map.get(edge.target)
                    s_name = source_name.name if source_name else edge.source
                    t_name = target_name.name if target_name else edge.target
                    warnings.append({
                        "type": "dependency_violation",
                        "message": (
                            f"'{t_name}' is in Wave {target_wave + 1} "
                            f"but depends on '{s_name}' in "
                            f"Wave {source_wave + 1}"
                        ),
                        "wave_id": None,
                        "workload_id": edge.target,
                    })

        # Check wave sizes
        if max_wave_size:
            for wave in waves:
                wl_count = len(wave.get("workload_ids", []))
                if wl_count > max_wave_size:
                    warnings.append({
                        "type": "oversize_wave",
                        "message": (
                            f"Wave '{wave.get('name', '')}' has "
                            f"{wl_count} workloads, exceeds max of "
                            f"{max_wave_size}"
                        ),
                        "wave_id": wave.get("id"),
                        "workload_id": None,
                    })

        # Check for unassigned workloads
        assigned = set(wave_assignment.keys())
        all_workloads = set(workload_map.keys())
        missing = all_workloads - assigned
        for wid in sorted(missing):
            w = workload_map.get(wid)
            warnings.append({
                "type": "missing_workload",
                "message": (
                    f"Workload '{w.name if w else wid}' "
                    f"is not assigned to any wave"
                ),
                "wave_id": None,
                "workload_id": wid,
            })

        return warnings

    def export_csv(self, waves_data: list[dict]) -> str:
        """Export wave plan as CSV.

        Args:
            waves_data: List of wave dicts with workload details.

        Returns:
            CSV string.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "Wave",
            "Wave Status",
            "Workload",
            "Type",
            "Criticality",
            "Strategy",
            "Dependencies",
        ])
        for wave in waves_data:
            for wl in wave.get("workloads", []):
                writer.writerow([
                    wave.get("name", ""),
                    wave.get("status", "planned"),
                    wl.get("name", ""),
                    wl.get("type", ""),
                    wl.get("criticality", ""),
                    wl.get("migration_strategy", ""),
                    "; ".join(wl.get("dependencies", [])),
                ])
        return output.getvalue()

    def export_markdown(self, waves_data: list[dict]) -> str:
        """Export wave plan as Markdown.

        Args:
            waves_data: List of wave dicts with workload details.

        Returns:
            Markdown string.
        """
        lines = ["# Migration Wave Plan", ""]
        for wave in waves_data:
            name = wave.get("name", "Wave")
            status = wave.get("status", "planned")
            workloads = wave.get("workloads", [])
            lines.append(f"## {name} ({status})")
            lines.append("")
            if workloads:
                lines.append(
                    "| Workload | Type | Criticality "
                    "| Strategy | Dependencies |"
                )
                lines.append(
                    "|----------|------|-------------|"
                    "----------|--------------|"
                )
                for wl in workloads:
                    deps = ", ".join(wl.get("dependencies", []))
                    lines.append(
                        f"| {wl.get('name', '')} "
                        f"| {wl.get('type', '')} "
                        f"| {wl.get('criticality', '')} "
                        f"| {wl.get('migration_strategy', '')} "
                        f"| {deps} |"
                    )
            else:
                lines.append("*No workloads assigned*")
            lines.append("")
        return "\n".join(lines)


wave_planner = WavePlanner()
