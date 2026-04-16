"""Pydantic schemas for sovereign compliance and service availability APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Sovereign Compliance Schemas ─────────────────────────────────────────────


class FrameworkControlResponse(BaseModel):
    """A single control family within a compliance framework."""

    id: str
    name: str
    description: str = ""
    control_count: int = 0


class SovereignFrameworkResponse(BaseModel):
    """Detailed view of a sovereign compliance framework."""

    short_name: str
    name: str
    description: str = ""
    version: str = ""
    cloud_environments: list[str] = Field(default_factory=list)
    control_families: list[FrameworkControlResponse] = Field(default_factory=list)
    total_controls: int = 0


class SovereignFrameworkSummary(BaseModel):
    """Summary view of a sovereign compliance framework (for list responses)."""

    short_name: str
    name: str
    description: str = ""
    version: str = ""
    cloud_environments: list[str] = Field(default_factory=list)
    control_family_count: int = 0


class SovereignFrameworkListResponse(BaseModel):
    """List of sovereign compliance frameworks."""

    frameworks: list[SovereignFrameworkSummary] = Field(default_factory=list)
    total: int = 0


# ── Compliance Evaluation Schemas ────────────────────────────────────────────


class FamilyScoreResult(BaseModel):
    """Per-family compliance score breakdown."""

    family_id: str
    family_name: str
    score: float | None = None
    status: str = "unknown"
    controls_evaluated: int = 0
    controls_met: int = 0


class SovereignComplianceResult(BaseModel):
    """Result of evaluating an architecture against a sovereign framework."""

    framework: str
    framework_name: str = ""
    overall_score: int = 0
    status: str = "unknown"
    total_controls_evaluated: int = 0
    total_controls_met: int = 0
    family_scores: list[FamilyScoreResult] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    message: str = ""


class EvaluateComplianceRequest(BaseModel):
    """Request body for sovereign compliance evaluation."""

    architecture: dict


# ── Service Availability Schemas ─────────────────────────────────────────────


class ServiceAvailabilityResponse(BaseModel):
    """Availability details for a single Azure service."""

    service_name: str
    category: str = ""
    commercial: bool = False
    government: bool = False
    china: bool = False
    notes: str = ""


class ServiceAvailabilityMatrixResponse(BaseModel):
    """Full service availability matrix."""

    environments: list[str] = Field(default_factory=list)
    services: list[dict] = Field(default_factory=list)
    by_category: dict[str, list[dict]] = Field(default_factory=dict)
    total_services: int = 0


class ArchitectureCompatibilityRequest(BaseModel):
    """Request body for architecture-to-environment compatibility check."""

    architecture: dict
    target_environment: str


class ArchitectureCompatibilityResponse(BaseModel):
    """Result of checking architecture compatibility with a target environment."""

    compatible: bool = False
    target_environment: str = ""
    services_checked: int = 0
    missing_services: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    alternatives: dict[str, str] = Field(default_factory=dict)
