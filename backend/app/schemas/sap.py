"""Pydantic schemas for SAP on Azure accelerator API endpoints."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Question Schemas ─────────────────────────────────────────────────────────


class SapQuestionResponse(BaseModel):
    """A single SAP-specific questionnaire question."""

    id: str = Field(..., description="Question identifier")
    text: str = Field(..., description="Question text")
    type: str = Field(
        ..., description="Input type (single_choice, multi_choice, numeric)"
    )
    options: list[dict] = Field(
        default_factory=list, description="Answer options"
    )
    required: bool = Field(True, description="Whether answer is required")
    category: str = Field("sap", description="Question category")
    help_text: str = Field("", description="Help text for the question")


class SapQuestionListResponse(BaseModel):
    """List of SAP questionnaire questions."""

    questions: list[SapQuestionResponse] = Field(default_factory=list)
    total: int = Field(0, description="Total number of questions")


# ── Architecture Schemas ─────────────────────────────────────────────────────


class SapArchitectureRequest(BaseModel):
    """Request to generate an SAP architecture."""

    answers: dict = Field(
        ..., description="Questionnaire answers keyed by question id"
    )


class SapArchitectureResponse(BaseModel):
    """Generated SAP architecture."""

    architecture: dict = Field(default_factory=dict)


# ── SKU Schemas ──────────────────────────────────────────────────────────────


class SapSkuResponse(BaseModel):
    """A SAP-certified VM SKU."""

    name: str
    series: str
    vcpus: int
    memory_gb: int
    saps_rating: int
    max_hana_memory_gb: int
    tier: str
    description: str = ""


class SapSkuListResponse(BaseModel):
    """List of SAP-certified VM SKUs."""

    skus: list[SapSkuResponse] = Field(default_factory=list)
    total: int = Field(0, description="Total number of SKUs")


# ── Sizing Schemas ───────────────────────────────────────────────────────────


class SapSizingRequest(BaseModel):
    """Request to estimate SAP VM sizing."""

    saps: int = Field(0, description="Required SAPS rating")
    data_volume: str = Field(
        "medium", description="Data volume: small, medium, large, very_large, ultra_large"
    )
    concurrent_users: int = Field(
        100, description="Peak concurrent users"
    )


class SapSizingResponse(BaseModel):
    """Sizing estimation result."""

    database_sku: dict = Field(default_factory=dict)
    app_server_sku: dict = Field(default_factory=dict)
    app_server_count: int = Field(0)
    total_saps: int = Field(0)
    estimated_memory_gb: int = Field(0)


# ── Best Practices Schemas ───────────────────────────────────────────────────


class SapBestPracticeResponse(BaseModel):
    """A single SAP on Azure best practice."""

    id: str
    category: str
    title: str
    description: str = ""
    severity: str = "high"
    link: str = ""


class SapBestPracticeListResponse(BaseModel):
    """List of SAP best practices."""

    best_practices: list[SapBestPracticeResponse] = Field(
        default_factory=list
    )
    total: int = Field(0)


# ── Bicep Schemas ────────────────────────────────────────────────────────────


class SapBicepRequest(BaseModel):
    """Request to generate SAP Bicep templates."""

    template_type: str = Field(
        ...,
        description=(
            "Template type: hana_vm, app_server, full_stack"
        ),
    )
    config: dict = Field(
        default_factory=dict,
        description="Template configuration parameters",
    )


class SapBicepResponse(BaseModel):
    """Generated Bicep template response."""

    template_type: str
    bicep_template: str = ""
    description: str = ""


# ── Validation Schemas ───────────────────────────────────────────────────────


class SapValidateRequest(BaseModel):
    """Request to validate an SAP architecture."""

    architecture: dict = Field(
        ..., description="SAP architecture dict to validate"
    )


class SapValidateResponse(BaseModel):
    """Architecture validation result."""

    valid: bool = Field(True)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


# ── Reference Architecture Schemas ───────────────────────────────────────────


class SapReferenceArchResponse(BaseModel):
    """A SAP reference architecture."""

    id: str
    name: str
    description: str = ""
    product: str = ""
    database: str = ""
    ha_enabled: bool = False
    dr_enabled: bool = False
    components: list[str] = Field(default_factory=list)
    link: str = ""


class SapReferenceArchListResponse(BaseModel):
    """List of SAP reference architectures."""

    reference_architectures: list[SapReferenceArchResponse] = Field(
        default_factory=list
    )
    total: int = Field(0)
