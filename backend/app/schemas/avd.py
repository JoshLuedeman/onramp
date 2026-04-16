"""Pydantic schemas for Azure Virtual Desktop accelerator APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Response Schemas ─────────────────────────────────────────────────────────


class AvdQuestionOption(BaseModel):
    """A single option within a questionnaire question."""

    value: str
    label: str


class AvdQuestionResponse(BaseModel):
    """A single AVD questionnaire question."""

    id: str
    category: str
    text: str
    type: str
    options: list[AvdQuestionOption] = Field(default_factory=list)
    required: bool = True
    order: int = 0


class AvdSkuResponse(BaseModel):
    """An AVD-optimised VM SKU."""

    name: str
    series: str
    family: str
    vcpus: int
    memory_gb: int
    gpu: bool = False
    users_per_vm: dict[str, int] = Field(default_factory=dict)
    recommended_users: int | None = None
    description: str = ""


class AvdSkuListResponse(BaseModel):
    """List of AVD VM SKUs."""

    skus: list[AvdSkuResponse] = Field(default_factory=list)
    total: int = 0


class AvdArchitectureResponse(BaseModel):
    """Generated AVD landing-zone architecture."""

    architecture: dict = Field(default_factory=dict)


class AvdBestPracticeResponse(BaseModel):
    """A single AVD best practice."""

    id: str
    title: str
    description: str
    category: str
    severity: str


class AvdSizingResponse(BaseModel):
    """Session-host sizing estimate."""

    session_host_count: int = 0
    users_per_host: int = 0
    recommended_sku: str = ""
    total_users: int = 0
    storage_gb: int = 0


class AvdValidationResponse(BaseModel):
    """Architecture validation result."""

    valid: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class AvdReferenceArchResponse(BaseModel):
    """An AVD reference architecture."""

    id: str
    name: str
    description: str
    user_count: str
    host_pool_type: str
    session_host_count: int
    vm_sku: str
    fslogix_storage: str
    regions: int
    scaling: str
    components: list[str] = Field(default_factory=list)


class AvdBicepResponse(BaseModel):
    """Generated Bicep template response."""

    template_type: str
    bicep_template: str = ""
    description: str = ""


# ── Request Schemas ──────────────────────────────────────────────────────────


class AvdSkuRequest(BaseModel):
    """Request body for SKU recommendations."""

    user_type: str = Field(
        default="knowledge_worker",
        description=(
            "User persona: task_worker, knowledge_worker,"
            " power_user, developer"
        ),
    )
    application_type: str = Field(
        default="office_productivity",
        description=(
            "Application workload: desktop_apps, web_apps,"
            " cad_3d, office_productivity"
        ),
    )


class AvdArchitectureRequest(BaseModel):
    """Request body for architecture generation."""

    answers: dict = Field(
        ...,
        description="Questionnaire answers keyed by question id.",
    )


class AvdSizingRequest(BaseModel):
    """Request body for sizing estimation."""

    requirements: dict = Field(
        ...,
        description=(
            "Requirements dict with user_count range string"
            " and optional user_type."
        ),
    )


class AvdValidationRequest(BaseModel):
    """Request body for architecture validation."""

    architecture: dict = Field(
        ...,
        description="Architecture dict to validate.",
    )


class AvdBicepRequest(BaseModel):
    """Request body for generating AVD Bicep templates."""

    template_type: str = Field(
        ...,
        description=(
            "Template type: host_pool, session_hosts, workspace,"
            " app_group, storage, networking, full_stack"
        ),
    )
    config: dict = Field(
        default_factory=dict,
        description="Template configuration parameters.",
    )
