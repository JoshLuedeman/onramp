"""Pydantic schemas for IoT landing zone accelerator APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Response Schemas ─────────────────────────────────────────────────────────


class IoTQuestionResponse(BaseModel):
    """A single IoT questionnaire question."""

    id: str
    text: str
    type: str
    options: list[str] = Field(default_factory=list)
    default: str = ""
    category: str = ""
    help_text: str = ""


class IoTQuestionsListResponse(BaseModel):
    """List of IoT questionnaire questions."""

    questions: list[IoTQuestionResponse] = Field(
        default_factory=list
    )
    total: int = 0


class IoTComponentResponse(BaseModel):
    """An IoT architecture component."""

    id: str
    name: str
    category: str = ""
    description: str = ""
    required: bool = False


class IoTSkuRecommendationResponse(BaseModel):
    """IoT Hub SKU recommendation result."""

    recommended_tier: dict = Field(default_factory=dict)
    units: int = 1
    estimated_daily_messages: int = 0
    device_count: int = 0
    rationale: str = ""
    alternatives: list[dict] = Field(default_factory=list)


class IoTArchitectureResponse(BaseModel):
    """Generated IoT architecture."""

    components: list[dict] = Field(default_factory=list)
    connections: list[dict] = Field(default_factory=list)
    iot_hub_tier: dict = Field(default_factory=dict)
    iot_hub_units: int = 1
    estimated_daily_messages: int = 0
    description: str = ""


class IoTBestPracticeResponse(BaseModel):
    """A single IoT best practice."""

    id: str
    category: str
    title: str
    description: str = ""
    priority: str = "medium"


class IoTBestPracticesListResponse(BaseModel):
    """List of IoT best practices."""

    best_practices: list[IoTBestPracticeResponse] = Field(
        default_factory=list
    )
    total: int = 0


class IoTSizingResponse(BaseModel):
    """IoT infrastructure sizing estimation."""

    iot_hub: dict = Field(default_factory=dict)
    storage: dict = Field(default_factory=dict)
    edge: dict = Field(default_factory=dict)
    event_hubs: dict = Field(default_factory=dict)
    stream_analytics: dict = Field(default_factory=dict)


class IoTValidationResponse(BaseModel):
    """IoT architecture validation result."""

    valid: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class IoTReferenceArchitectureResponse(BaseModel):
    """A single IoT reference architecture."""

    id: str
    name: str
    description: str = ""
    components: list[str] = Field(default_factory=list)
    device_types: list[str] = Field(default_factory=list)
    protocols: list[str] = Field(default_factory=list)
    scale: str = ""
    use_cases: list[str] = Field(default_factory=list)


class IoTReferenceArchitecturesListResponse(BaseModel):
    """List of IoT reference architectures."""

    architectures: list[IoTReferenceArchitectureResponse] = Field(
        default_factory=list
    )
    total: int = 0


class IoTBicepResponse(BaseModel):
    """Generated Bicep template response."""

    template_type: str
    bicep_template: str = ""
    description: str = ""


# ── Request Schemas ──────────────────────────────────────────────────────────


class IoTSkuRecommendationRequest(BaseModel):
    """Request body for IoT Hub SKU recommendation."""

    answers: dict = Field(
        ...,
        description=(
            "Questionnaire answers mapping question IDs to"
            " selected values."
        ),
    )


class IoTArchitectureRequest(BaseModel):
    """Request body for IoT architecture generation."""

    answers: dict = Field(
        ...,
        description=(
            "Questionnaire answers mapping question IDs to"
            " selected values."
        ),
    )


class IoTSizingRequest(BaseModel):
    """Request body for IoT sizing estimation."""

    requirements: dict = Field(
        ...,
        description=(
            "Sizing requirements: device_count,"
            " message_frequency, message_size_kb,"
            " retention_days, edge_nodes."
        ),
    )


class IoTValidationRequest(BaseModel):
    """Request body for IoT architecture validation."""

    architecture: dict = Field(
        ...,
        description=(
            "Architecture dict with a 'components' list of"
            " component dicts."
        ),
    )


class IoTBicepRequest(BaseModel):
    """Request body for generating IoT Bicep templates."""

    template_type: str = Field(
        ...,
        description=(
            "Template type: iot_hub, dps, event_hub,"
            " stream_analytics, storage, adx, full_stack."
        ),
    )
    config: dict = Field(
        default_factory=dict,
        description="Template configuration parameters.",
    )
