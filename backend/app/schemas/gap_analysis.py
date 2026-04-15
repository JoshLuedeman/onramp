"""Gap analysis schemas — request/response models for gap analysis."""

from enum import Enum

from pydantic import BaseModel, Field


class GapSeverity(str, Enum):
    """Severity level for a gap finding."""
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class GapCategory(str, Enum):
    """CAF design area category for gap findings."""
    management_groups = "management_groups"
    policy = "policy"
    rbac = "rbac"
    networking = "networking"
    monitoring = "monitoring"
    security = "security"
    naming = "naming"


class GapFinding(BaseModel):
    """A single gap finding from the analysis."""
    id: str
    category: GapCategory
    severity: GapSeverity
    title: str
    description: str
    remediation: str
    caf_reference: str | None = None
    can_auto_remediate: bool = False


class GapAnalysisRequest(BaseModel):
    """Request to run gap analysis on a discovery scan."""
    use_ai: bool = Field(default=False, description="Use AI for deeper analysis")


class DiscoveredAnswer(BaseModel):
    """A questionnaire answer suggested by discovery scan."""
    value: str | list[str]
    confidence: str = Field(
        default="medium",
        description="Confidence level: high, medium, low",
    )
    evidence: str = Field(
        default="",
        description="What discovery evidence supports this answer",
    )
    source: str = "discovered"


class GapAnalysisResponse(BaseModel):
    """Response containing all gap findings for a scan."""
    scan_id: str
    total_findings: int
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    findings: list[GapFinding] = Field(default_factory=list)
    areas_checked: list[str] = Field(default_factory=list)
    areas_skipped: list[str] = Field(default_factory=list)


class BrownfieldContext(BaseModel):
    """Context for brownfield questionnaire flow."""
    scan_id: str
    discovered_answers: dict[str, DiscoveredAnswer] = Field(
        default_factory=dict,
    )
    gap_summary: dict[str, int] = Field(default_factory=dict)
