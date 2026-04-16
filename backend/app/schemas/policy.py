"""Pydantic schemas for policy generation API.

Defines request/response models for natural language policy creation,
validation, and the built-in policy template library.
"""

from pydantic import BaseModel, Field


class PolicyGenerateRequest(BaseModel):
    """Request to generate an Azure Policy from a natural language description."""

    description: str
    context: dict | None = None


class PolicyDefinition(BaseModel):
    """A generated Azure Policy definition."""

    name: str
    display_name: str = ""
    description: str = ""
    mode: str = "All"
    policy_rule: dict = Field(default_factory=dict)
    parameters: dict = Field(default_factory=dict)
    metadata: dict = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class PolicyValidationResult(BaseModel):
    """Result of validating a policy JSON structure."""

    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class PolicyTemplate(BaseModel):
    """A pre-built policy template from the library."""

    id: str
    name: str
    description: str
    category: str
    policy_json: dict = Field(default_factory=dict)


class PolicyLibraryResponse(BaseModel):
    """Response containing available policy templates."""

    policies: list[PolicyTemplate] = Field(default_factory=list)


class PolicyApplyRequest(BaseModel):
    """Request to apply a generated policy to an architecture."""

    policy: dict
    architecture_id: str | None = None
