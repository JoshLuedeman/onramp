"""Pydantic schemas for dependency graph API."""

from pydantic import BaseModel, Field


class WorkloadSummary(BaseModel):
    """Minimal workload info used in the dependency graph."""

    id: str
    name: str
    criticality: str
    migration_strategy: str
    project_id: str


class DependencyEdge(BaseModel):
    """A directed edge in the dependency graph."""

    source: str
    target: str
    dependency_type: str = "depends_on"


class DependencyGraph(BaseModel):
    """Full dependency graph for a project."""

    nodes: list[WorkloadSummary] = Field(default_factory=list)
    edges: list[DependencyEdge] = Field(default_factory=list)
    circular_dependencies: list[list[str]] = Field(default_factory=list)
    migration_groups: list[list[str]] = Field(default_factory=list)


class AddDependencyRequest(BaseModel):
    """Request body for adding a dependency link."""

    target_workload_id: str
    dependency_type: str = "depends_on"


class MigrationOrderResponse(BaseModel):
    """Suggested migration order with groups and warnings."""

    order: list[str] = Field(default_factory=list)
    migration_groups: list[list[str]] = Field(default_factory=list)
    circular_dependencies: list[list[str]] = Field(default_factory=list)
    has_circular: bool = False
    workload_names: dict[str, str] = Field(default_factory=dict)
