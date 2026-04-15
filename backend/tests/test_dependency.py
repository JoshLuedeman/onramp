"""Tests for dependency graph analysis — service and API routes."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.main import app
from app.models import Base
from app.schemas.dependency import DependencyEdge, DependencyGraph, WorkloadSummary
from app.services.dependency_analyzer import DependencyAnalyzer
from tests.conftest import SQLITE_TEST_URL

client = TestClient(app)

# ---------------------------------------------------------------------------
# DependencyAnalyzer unit tests
# ---------------------------------------------------------------------------


def _make_summary(wid: str) -> WorkloadSummary:
    return WorkloadSummary(
        id=wid,
        name=f"Workload-{wid}",
        criticality="standard",
        migration_strategy="rehost",
        project_id="proj-1",
    )


def _make_graph(
    ids: list[str],
    edge_pairs: list[tuple[str, str]],
) -> DependencyGraph:
    nodes = [_make_summary(i) for i in ids]
    edges = [DependencyEdge(source=s, target=t) for s, t in edge_pairs]
    return DependencyGraph(nodes=nodes, edges=edges)


class TestDependencyAnalyzerService:
    def setup_method(self):
        self.analyzer = DependencyAnalyzer()

    # --- get_dependency_graph ---

    def test_get_dependency_graph_empty(self):
        graph = self.analyzer.get_dependency_graph([])
        assert graph.nodes == []
        assert graph.edges == []
        assert graph.circular_dependencies == []
        assert graph.migration_groups == []

    def test_get_dependency_graph_no_edges(self):
        nodes = [_make_summary("a"), _make_summary("b")]
        graph = self.analyzer.get_dependency_graph(nodes, [])
        assert len(graph.nodes) == 2
        assert graph.edges == []
        assert graph.circular_dependencies == []
        # Each node is its own group
        assert sorted(sorted(g) for g in graph.migration_groups) == [["a"], ["b"]]

    def test_get_dependency_graph_with_edges(self):
        nodes = [_make_summary("a"), _make_summary("b"), _make_summary("c")]
        edges = [
            DependencyEdge(source="a", target="b"),
            DependencyEdge(source="b", target="c"),
        ]
        graph = self.analyzer.get_dependency_graph(nodes, edges)
        assert len(graph.edges) == 2
        assert graph.circular_dependencies == []
        # All connected in one group
        assert len(graph.migration_groups) == 1
        assert sorted(graph.migration_groups[0]) == ["a", "b", "c"]

    def test_get_dependency_graph_ignores_unknown_target(self):
        nodes = [_make_summary("a")]
        edges = [DependencyEdge(source="a", target="unknown-id")]
        graph = self.analyzer.get_dependency_graph(nodes, edges)
        # Edge references unknown node — should be ignored when building adj
        assert graph.circular_dependencies == []

    # --- find_circular_dependencies ---

    def test_no_cycles_linear(self):
        graph = _make_graph(["a", "b", "c"], [("a", "b"), ("b", "c")])
        cycles = self.analyzer.find_circular_dependencies(graph)
        assert cycles == []

    def test_simple_cycle(self):
        graph = _make_graph(["a", "b"], [("a", "b"), ("b", "a")])
        cycles = self.analyzer.find_circular_dependencies(graph)
        assert len(cycles) == 1
        assert set(cycles[0]) == {"a", "b"}

    def test_three_node_cycle(self):
        graph = _make_graph(
            ["a", "b", "c"],
            [("a", "b"), ("b", "c"), ("c", "a")],
        )
        cycles = self.analyzer.find_circular_dependencies(graph)
        assert len(cycles) == 1
        assert set(cycles[0]) == {"a", "b", "c"}

    def test_self_loop_cycle(self):
        graph = _make_graph(["a"], [("a", "a")])
        cycles = self.analyzer.find_circular_dependencies(graph)
        assert len(cycles) == 1

    def test_multiple_separate_cycles(self):
        graph = _make_graph(
            ["a", "b", "c", "d"],
            [("a", "b"), ("b", "a"), ("c", "d"), ("d", "c")],
        )
        cycles = self.analyzer.find_circular_dependencies(graph)
        assert len(cycles) == 2

    # --- find_migration_groups ---

    def test_migration_groups_disconnected(self):
        graph = _make_graph(["a", "b", "c"], [])
        groups = self.analyzer.find_migration_groups(graph)
        assert len(groups) == 3

    def test_migration_groups_connected(self):
        graph = _make_graph(["a", "b", "c"], [("a", "b"), ("b", "c")])
        groups = self.analyzer.find_migration_groups(graph)
        assert len(groups) == 1
        assert sorted(groups[0]) == ["a", "b", "c"]

    def test_migration_groups_partial(self):
        graph = _make_graph(["a", "b", "c", "d"], [("a", "b")])
        groups = self.analyzer.find_migration_groups(graph)
        assert len(groups) == 3

    # --- suggest_migration_order ---

    def test_topological_order_linear(self):
        graph = _make_graph(["a", "b", "c"], [("a", "b"), ("b", "c")])
        order = self.analyzer.suggest_migration_order(graph)
        assert order.index("a") < order.index("b")
        assert order.index("b") < order.index("c")

    def test_topological_order_no_edges(self):
        graph = _make_graph(["a", "b", "c"], [])
        order = self.analyzer.suggest_migration_order(graph)
        assert set(order) == {"a", "b", "c"}

    def test_topological_order_raises_on_cycle(self):
        graph = _make_graph(["a", "b"], [("a", "b"), ("b", "a")])
        with pytest.raises(ValueError, match="circular"):
            self.analyzer.suggest_migration_order(graph)

    def test_topological_order_diamond(self):
        # a → b, a → c, b → d, c → d
        graph = _make_graph(
            ["a", "b", "c", "d"],
            [("a", "b"), ("a", "c"), ("b", "d"), ("c", "d")],
        )
        order = self.analyzer.suggest_migration_order(graph)
        assert order.index("a") < order.index("b")
        assert order.index("a") < order.index("c")
        assert order.index("b") < order.index("d")
        assert order.index("c") < order.index("d")


# ---------------------------------------------------------------------------
# API route tests — no-DB mode
# ---------------------------------------------------------------------------


class TestDependencyRoutesNoDb:
    def test_get_dependency_graph_no_db(self):
        r = client.get("/api/workloads/dependency-graph?project_id=test-proj")
        assert r.status_code == 200
        data = r.json()
        assert "nodes" in data
        assert "edges" in data

    def test_get_migration_order_no_db(self):
        r = client.get("/api/workloads/migration-order?project_id=test-proj")
        assert r.status_code == 200
        data = r.json()
        assert "order" in data
        assert "migration_groups" in data
        assert "circular_dependencies" in data
        assert "has_circular" in data

    def test_add_dependency_no_db(self):
        r = client.post(
            "/api/workloads/wl-1/dependencies",
            json={"target_workload_id": "wl-2"},
        )
        assert r.status_code == 503

    def test_remove_dependency_no_db(self):
        r = client.delete("/api/workloads/wl-1/dependencies/wl-2")
        assert r.status_code == 503

    def test_dependency_graph_missing_project_id(self):
        r = client.get("/api/workloads/dependency-graph")
        assert r.status_code == 422

    def test_migration_order_missing_project_id(self):
        r = client.get("/api/workloads/migration-order")
        assert r.status_code == 422


# ---------------------------------------------------------------------------
# API route tests — with real SQLite DB
# ---------------------------------------------------------------------------


@pytest.fixture
async def db_session():
    engine = create_async_engine(SQLITE_TEST_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_dependency_graph_db_path(db_session):
    """Test GET /dependency-graph with a real DB session."""
    from app.api.routes.workloads import get_dependency_graph
    from app.models.project import Project
    from app.models.workload import Workload
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    proj = Project(
        id="dep-proj-1",
        name="Dep Test Project",
        tenant_id="dev-tenant",
        created_at=now,
        updated_at=now,
    )
    db_session.add(proj)
    wl_a = Workload(
        id="dep-wl-a",
        project_id="dep-proj-1",
        name="WL A",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=["dep-wl-b"],
        created_at=now,
        updated_at=now,
    )
    wl_b = Workload(
        id="dep-wl-b",
        project_id="dep-proj-1",
        name="WL B",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=[],
        created_at=now,
        updated_at=now,
    )
    db_session.add(wl_a)
    db_session.add(wl_b)
    await db_session.flush()

    graph = await get_dependency_graph(
        project_id="dep-proj-1",
        user={"sub": "dev", "tid": "dev-tenant"},
        db=db_session,
    )
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    edge = graph.edges[0]
    assert edge.source == "dep-wl-a"
    assert edge.target == "dep-wl-b"


@pytest.mark.asyncio
async def test_add_and_remove_dependency_db(db_session):
    """Test POST and DELETE /dependencies with a real DB session."""
    from app.api.routes.workloads import add_dependency, remove_dependency
    from app.models.project import Project
    from app.models.workload import Workload
    from app.schemas.dependency import AddDependencyRequest
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    proj = Project(
        id="dep-proj-2",
        name="Dep Test 2",
        tenant_id="dev-tenant",
        created_at=now,
        updated_at=now,
    )
    db_session.add(proj)
    wl1 = Workload(
        id="dep-wl-1",
        project_id="dep-proj-2",
        name="WL 1",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=[],
        created_at=now,
        updated_at=now,
    )
    wl2 = Workload(
        id="dep-wl-2",
        project_id="dep-proj-2",
        name="WL 2",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=[],
        created_at=now,
        updated_at=now,
    )
    db_session.add(wl1)
    db_session.add(wl2)
    await db_session.flush()

    user = {"sub": "dev", "tid": "dev-tenant"}

    # Add dependency
    resp = await add_dependency(
        workload_id="dep-wl-1",
        body=AddDependencyRequest(target_workload_id="dep-wl-2"),
        user=user,
        db=db_session,
    )
    assert "dep-wl-2" in (resp.dependencies or [])

    # Adding same dependency again is idempotent
    resp2 = await add_dependency(
        workload_id="dep-wl-1",
        body=AddDependencyRequest(target_workload_id="dep-wl-2"),
        user=user,
        db=db_session,
    )
    assert resp2.dependencies.count("dep-wl-2") == 1

    # Remove dependency
    resp3 = await remove_dependency(
        workload_id="dep-wl-1",
        target_id="dep-wl-2",
        user=user,
        db=db_session,
    )
    assert "dep-wl-2" not in (resp3.dependencies or [])

    # Removing non-existent dependency is safe
    resp4 = await remove_dependency(
        workload_id="dep-wl-1",
        target_id="dep-wl-2",
        user=user,
        db=db_session,
    )
    assert resp4 is not None


@pytest.mark.asyncio
async def test_migration_order_db_path(db_session):
    """Test GET /migration-order with a real DB session."""
    from app.api.routes.workloads import get_migration_order
    from app.models.project import Project
    from app.models.workload import Workload
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    proj = Project(
        id="dep-proj-3",
        name="Migration Order Test",
        tenant_id="dev-tenant",
        created_at=now,
        updated_at=now,
    )
    db_session.add(proj)
    wl_x = Workload(
        id="dep-wl-x",
        project_id="dep-proj-3",
        name="WL X",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=["dep-wl-y"],
        created_at=now,
        updated_at=now,
    )
    wl_y = Workload(
        id="dep-wl-y",
        project_id="dep-proj-3",
        name="WL Y",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=[],
        created_at=now,
        updated_at=now,
    )
    db_session.add(wl_x)
    db_session.add(wl_y)
    await db_session.flush()

    result = await get_migration_order(
        project_id="dep-proj-3",
        user={"sub": "dev", "tid": "dev-tenant"},
        db=db_session,
    )
    assert result.has_circular is False
    assert "dep-wl-x" in result.order
    assert "dep-wl-y" in result.order
    assert result.order.index("dep-wl-y") < result.order.index("dep-wl-x")


@pytest.mark.asyncio
async def test_migration_order_with_cycle(db_session):
    """Test migration-order returns has_circular when cycles exist."""
    from app.api.routes.workloads import get_migration_order
    from app.models.project import Project
    from app.models.workload import Workload
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    proj = Project(
        id="dep-proj-4",
        name="Circular Test",
        tenant_id="dev-tenant",
        created_at=now,
        updated_at=now,
    )
    db_session.add(proj)
    wl_p = Workload(
        id="dep-wl-p",
        project_id="dep-proj-4",
        name="WL P",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=["dep-wl-q"],
        created_at=now,
        updated_at=now,
    )
    wl_q = Workload(
        id="dep-wl-q",
        project_id="dep-proj-4",
        name="WL Q",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=["dep-wl-p"],
        created_at=now,
        updated_at=now,
    )
    db_session.add(wl_p)
    db_session.add(wl_q)
    await db_session.flush()

    result = await get_migration_order(
        project_id="dep-proj-4",
        user={"sub": "dev", "tid": "dev-tenant"},
        db=db_session,
    )
    assert result.has_circular is True
    assert len(result.circular_dependencies) > 0


@pytest.mark.asyncio
async def test_add_dependency_404_target(db_session):
    """Test adding a dependency to a non-existent target raises 404."""
    from fastapi import HTTPException
    from app.api.routes.workloads import add_dependency
    from app.models.project import Project
    from app.models.workload import Workload
    from app.schemas.dependency import AddDependencyRequest
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    proj = Project(
        id="dep-proj-5",
        name="404 Test",
        tenant_id="dev-tenant",
        created_at=now,
        updated_at=now,
    )
    db_session.add(proj)
    wl = Workload(
        id="dep-wl-only",
        project_id="dep-proj-5",
        name="Solo WL",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=[],
        created_at=now,
        updated_at=now,
    )
    db_session.add(wl)
    await db_session.flush()

    with pytest.raises(HTTPException) as exc_info:
        await add_dependency(
            workload_id="dep-wl-only",
            body=AddDependencyRequest(target_workload_id="nonexistent"),
            user={"sub": "dev", "tid": "dev-tenant"},
            db=db_session,
        )
    assert exc_info.value.status_code == 404


# ---------------------------------------------------------------------------
# Helper function tests — test _workloads_to_graph directly (no DB needed)
# ---------------------------------------------------------------------------


def test_workloads_to_graph_empty():
    """_workloads_to_graph returns an empty graph for an empty list."""
    from app.api.routes.workloads import _workloads_to_graph
    graph = _workloads_to_graph([])
    assert graph.nodes == []
    assert graph.edges == []


def test_workloads_to_graph_no_dependencies():
    """_workloads_to_graph with workloads that have no dependencies."""
    from app.api.routes.workloads import _workloads_to_graph
    from app.models.workload import Workload
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    wl = Workload(
        id="helper-wl-1",
        project_id="helper-proj",
        name="Helper WL",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=[],
        created_at=now,
        updated_at=now,
    )
    graph = _workloads_to_graph([wl])
    assert len(graph.nodes) == 1
    assert graph.nodes[0].id == "helper-wl-1"
    assert graph.edges == []


def test_workloads_to_graph_with_dependencies():
    """_workloads_to_graph creates edges from the dependencies field."""
    from app.api.routes.workloads import _workloads_to_graph
    from app.models.workload import Workload
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    wl_a = Workload(
        id="helper-wl-a",
        project_id="helper-proj",
        name="WL A",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=["helper-wl-b"],
        created_at=now,
        updated_at=now,
    )
    wl_b = Workload(
        id="helper-wl-b",
        project_id="helper-proj",
        name="WL B",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=[],
        created_at=now,
        updated_at=now,
    )
    graph = _workloads_to_graph([wl_a, wl_b])
    assert len(graph.nodes) == 2
    assert len(graph.edges) == 1
    assert graph.edges[0].source == "helper-wl-a"
    assert graph.edges[0].target == "helper-wl-b"


def test_workloads_to_graph_ignores_external_dependencies():
    """_workloads_to_graph ignores dependencies that reference unknown IDs."""
    from app.api.routes.workloads import _workloads_to_graph
    from app.models.workload import Workload
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    wl = Workload(
        id="helper-wl-x",
        project_id="helper-proj",
        name="WL X",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=["nonexistent-id"],
        created_at=now,
        updated_at=now,
    )
    graph = _workloads_to_graph([wl])
    # Edge not created — target doesn't exist in node set
    assert graph.edges == []


def test_workloads_to_graph_with_circular_dependencies():
    """_workloads_to_graph detects and reports circular dependencies."""
    from app.api.routes.workloads import _workloads_to_graph
    from app.models.workload import Workload
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    wl_p = Workload(
        id="circ-wl-p",
        project_id="helper-proj",
        name="P",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=["circ-wl-q"],
        created_at=now,
        updated_at=now,
    )
    wl_q = Workload(
        id="circ-wl-q",
        project_id="helper-proj",
        name="Q",
        criticality="standard",
        migration_strategy="rehost",
        dependencies=["circ-wl-p"],
        created_at=now,
        updated_at=now,
    )
    graph = _workloads_to_graph([wl_p, wl_q])
    assert len(graph.circular_dependencies) == 1


def test_workloads_to_graph_none_dependencies():
    """_workloads_to_graph handles None dependencies gracefully."""
    from app.api.routes.workloads import _workloads_to_graph
    from app.models.workload import Workload
    from datetime import datetime, timezone

    now = datetime.now(timezone.utc)
    wl = Workload(
        id="none-dep-wl",
        project_id="helper-proj",
        name="WL None Deps",
        criticality="mission-critical",
        migration_strategy="replace",
        dependencies=None,
        created_at=now,
        updated_at=now,
    )
    graph = _workloads_to_graph([wl])
    assert len(graph.nodes) == 1
    assert graph.edges == []
