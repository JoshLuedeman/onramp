"""Security posture advisor schemas."""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """Security finding severity levels."""

    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class SecurityFinding(BaseModel):
    """A single security finding from analysis."""

    id: str
    severity: Severity
    category: str
    resource: str
    finding: str
    remediation: str = ""
    auto_fixable: bool = False


class SecurityAnalysisResult(BaseModel):
    """Result of a complete security analysis."""

    score: int = Field(ge=0, le=100)
    findings: list[SecurityFinding] = Field(default_factory=list)
    summary: str = ""
    analyzed_at: datetime = Field(default_factory=datetime.utcnow)


class SecurityAnalyzeRequest(BaseModel):
    """Request body for security analysis."""

    architecture: dict
    use_ai: bool = False


class RemediationStep(BaseModel):
    """Remediation step for a specific finding."""

    finding_id: str
    description: str
    architecture_changes: dict = Field(default_factory=dict)


class SecurityCheck(BaseModel):
    """Describes an available security check."""

    id: str
    name: str
    description: str
    category: str
    severity: Severity
