"""Tests for wave planner service."""

import pytest

from app.schemas.dependency import DependencyEdge, WorkloadSummary
from app.services.wave_planner import WavePlanner


def _ws(
    wid: str,
    name: str = "",
    criticality: str = "standard",
    strategy: str = "rehost",
) -> WorkloadSummary:
    return WorkloadSummary(
        id=wid,
        name=name or f"Workload-{wid}",
        criticality=criticality,
        migration_strategy=strategy,
        project_id="proj-1",
    )


class TestGenerateWaves:
    def setup_method(self):
        self.planner = WavePlanner()

    def test_generate_waves_empty(self):
        result = self.planner.generate_waves([])
        assert result == []

    def test_generate_waves_no_dependencies(self):
        workloads = [
            _ws("a", strategy="rebuild"),
            _ws("b", strategy="rehost"),
            _ws("c", strategy="refactor"),
        ]
        waves = self.planner.generate_waves(workloads)
        assert len(waves) == 1
        ids = [w.id for w in waves[0]]
        # rehost < refactor < rebuild in complexity
        assert ids == ["b", "c", "a"]

    def test_generate_waves_with_dependencies(self):
        workloads = [_ws("a"), _ws("b"), _ws("c")]
        edges = [
            DependencyEdge(source="a", target="b"),
            DependencyEdge(source="b", target="c"),
        ]
        waves = self.planner.generate_waves(workloads, edges)
        assert len(waves) == 3
        assert waves[0][0].id == "a"
        assert waves[1][0].id == "b"
        assert waves[2][0].id == "c"

    def test_generate_waves_with_cycles(self):
        workloads = [_ws("a"), _ws("b"), _ws("c"), _ws("d")]
        edges = [
            DependencyEdge(source="a", target="b"),
            DependencyEdge(source="b", target="a"),  # cycle
            DependencyEdge(source="c", target="d"),
        ]
        waves = self.planner.generate_waves(workloads, edges)
        # c, d are non-cycle; a, b are cycle nodes placed last
        assert len(waves) >= 2
        all_ids = [w.id for wave in waves for w in wave]
        assert set(all_ids) == {"a", "b", "c", "d"}
        # Cycle nodes should be in the last wave
        last_ids = {w.id for w in waves[-1]}
        assert "a" in last_ids
        assert "b" in last_ids

    def test_generate_waves_max_size(self):
        workloads = [_ws(f"w{i}") for i in range(6)]
        waves = self.planner.generate_waves(
            workloads, max_wave_size=2
        )
        for wave in waves:
            assert len(wave) <= 2
        all_ids = {w.id for wave in waves for w in wave}
        assert len(all_ids) == 6

    def test_generate_waves_priority_strategy(self):
        workloads = [
            _ws("a", criticality="dev-test", strategy="rehost"),
            _ws("b", criticality="mission-critical", strategy="rehost"),
            _ws("c", criticality="standard", strategy="rehost"),
        ]
        waves = self.planner.generate_waves(
            workloads, strategy="priority_first"
        )
        assert len(waves) == 1
        ids = [w.id for w in waves[0]]
        # priority_first: mission-critical=0, standard=2, dev-test=3
        assert ids[0] == "b"
        assert ids[-1] == "a"

    def test_generate_waves_complexity_first_strategy(self):
        workloads = [
            _ws("a", criticality="dev-test", strategy="rehost"),
            _ws("b", criticality="mission-critical", strategy="rehost"),
            _ws("c", criticality="standard", strategy="rehost"),
        ]
        waves = self.planner.generate_waves(
            workloads, strategy="complexity_first"
        )
        assert len(waves) == 1
        ids = [w.id for w in waves[0]]
        # complexity_first: dev-test=0, standard=1, mission-critical=3
        assert ids[0] == "a"
        assert ids[-1] == "b"


class TestValidateWaves:
    def setup_method(self):
        self.planner = WavePlanner()

    def test_validate_dependency_violation(self):
        workload_map = {
            "a": _ws("a", name="Alpha"),
            "b": _ws("b", name="Beta"),
        }
        edges = [DependencyEdge(source="a", target="b")]
        waves = [
            {"id": "w1", "name": "Wave 1", "order": 0, "workload_ids": ["b"]},
            {"id": "w2", "name": "Wave 2", "order": 1, "workload_ids": ["a"]},
        ]
        warnings = self.planner.validate_waves(
            waves, workload_map, edges
        )
        assert len(warnings) == 1
        assert warnings[0]["type"] == "dependency_violation"
        assert "Beta" in warnings[0]["message"]
        assert "Alpha" in warnings[0]["message"]

    def test_validate_oversize_wave(self):
        workload_map = {
            "a": _ws("a"),
            "b": _ws("b"),
            "c": _ws("c"),
        }
        waves = [
            {
                "id": "w1",
                "name": "Wave 1",
                "order": 0,
                "workload_ids": ["a", "b", "c"],
            },
        ]
        warnings = self.planner.validate_waves(
            waves, workload_map, [], max_wave_size=2
        )
        assert len(warnings) == 1
        assert warnings[0]["type"] == "oversize_wave"

    def test_validate_missing_workloads(self):
        workload_map = {
            "a": _ws("a", name="Alpha"),
            "b": _ws("b", name="Beta"),
        }
        waves = [
            {"id": "w1", "name": "Wave 1", "order": 0, "workload_ids": ["a"]},
        ]
        warnings = self.planner.validate_waves(
            waves, workload_map, []
        )
        assert len(warnings) == 1
        assert warnings[0]["type"] == "missing_workload"
        assert "Beta" in warnings[0]["message"]

    def test_validate_no_warnings(self):
        workload_map = {
            "a": _ws("a"),
            "b": _ws("b"),
        }
        edges = [DependencyEdge(source="a", target="b")]
        waves = [
            {"id": "w1", "name": "Wave 1", "order": 0, "workload_ids": ["a"]},
            {"id": "w2", "name": "Wave 2", "order": 1, "workload_ids": ["b"]},
        ]
        warnings = self.planner.validate_waves(
            waves, workload_map, edges
        )
        assert warnings == []


class TestExport:
    def setup_method(self):
        self.planner = WavePlanner()
        self.waves_data = [
            {
                "name": "Wave 1",
                "status": "planned",
                "workloads": [
                    {
                        "name": "VM-1",
                        "type": "vm",
                        "criticality": "standard",
                        "migration_strategy": "rehost",
                        "dependencies": ["DB-1"],
                    },
                ],
            },
            {
                "name": "Wave 2",
                "status": "planned",
                "workloads": [
                    {
                        "name": "DB-1",
                        "type": "database",
                        "criticality": "business-critical",
                        "migration_strategy": "refactor",
                        "dependencies": [],
                    },
                ],
            },
        ]

    def test_export_csv(self):
        result = self.planner.export_csv(self.waves_data)
        assert "Wave,Wave Status,Workload" in result
        assert "VM-1" in result
        assert "DB-1" in result
        lines = result.strip().split("\n")
        assert len(lines) == 3  # header + 2 data rows

    def test_export_markdown(self):
        result = self.planner.export_markdown(self.waves_data)
        assert "# Migration Wave Plan" in result
        assert "## Wave 1 (planned)" in result
        assert "## Wave 2 (planned)" in result
        assert "VM-1" in result
        assert "DB-1" in result
        assert "| Workload |" in result

    def test_export_csv_empty(self):
        result = self.planner.export_csv([])
        lines = result.strip().split("\n")
        assert len(lines) == 1  # header only

    def test_export_markdown_empty_wave(self):
        result = self.planner.export_markdown([
            {"name": "Wave 1", "status": "planned", "workloads": []}
        ])
        assert "*No workloads assigned*" in result
