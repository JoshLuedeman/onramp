"""Pydantic schemas for the AI/ML landing zone accelerator."""

from pydantic import BaseModel, Field

# ── Question Schemas ─────────────────────────────────────────────────────

class AiMlQuestionOption(BaseModel):
    """Single option in a multi-choice question."""
    value: str
    label: str


class AiMlQuestionResponse(BaseModel):
    """Single AI/ML questionnaire question."""
    id: str
    text: str
    type: str
    options: list[AiMlQuestionOption] = Field(default_factory=list)
    required: bool = True
    category: str = "ai_ml"
    help_text: str = ""


# ── Architecture Schemas ─────────────────────────────────────────────────

class AiMlArchitectureRequest(BaseModel):
    """Request body for AI/ML architecture generation."""
    answers: dict = Field(
        default_factory=dict,
        description="Questionnaire answers keyed by question id.",
    )


class AiMlArchitectureResponse(BaseModel):
    """Generated AI/ML architecture."""
    architecture: dict = Field(default_factory=dict)


# ── SKU Schemas ──────────────────────────────────────────────────────────

class AiMlSkuRecommendation(BaseModel):
    """Single GPU SKU recommendation."""
    id: str
    name: str
    family: str
    gpu_type: str
    gpu_count: int
    gpu_memory_gb: int
    vcpus: int
    ram_gb: int
    use_case: str
    price_tier: str


# ── Sizing Schemas ───────────────────────────────────────────────────────

class AiMlSizingRequest(BaseModel):
    """Request body for AI/ML sizing estimation."""
    requirements: dict = Field(
        default_factory=dict,
        description="Workload requirements for sizing estimation.",
    )


class AiMlSizingResponse(BaseModel):
    """Sizing estimation result."""
    sizing: dict = Field(default_factory=dict)


# ── Bicep Schemas ────────────────────────────────────────────────────────

class AiMlBicepRequest(BaseModel):
    """Request body for AI/ML Bicep generation."""
    config: dict = Field(
        default_factory=dict,
        description="Configuration for Bicep generation.",
    )
    template_type: str = Field(
        default="full_stack",
        description="One of: ml_workspace, compute_cluster, full_stack.",
    )


class AiMlBicepResponse(BaseModel):
    """Generated Bicep template."""
    bicep: str
    template_type: str


# ── Validation Schemas ───────────────────────────────────────────────────

class AiMlValidationRequest(BaseModel):
    """Request body for AI/ML architecture validation."""
    architecture: dict = Field(default_factory=dict)


class AiMlValidationResponse(BaseModel):
    """AI/ML architecture validation result."""
    valid: bool
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


# ── Reference Architecture Schemas ───────────────────────────────────────

class ReferenceArchitectureResponse(BaseModel):
    """Single reference architecture."""
    id: str
    name: str
    description: str
    team_size: str
    use_case: str
    services: list[str] = Field(default_factory=list)
    estimated_monthly_cost_usd: int
    gpu_type: str
    mlops_level: str
