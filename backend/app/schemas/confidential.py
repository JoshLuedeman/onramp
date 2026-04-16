"""Pydantic schemas for Azure Confidential Computing APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field

# ── Response Schemas ─────────────────────────────────────────────────────────


class ConfidentialOptionResponse(BaseModel):
    """A single confidential computing option."""

    id: str
    name: str
    category: str
    tee_types: list[str] = Field(default_factory=list)
    description: str = ""
    use_cases: list[str] = Field(default_factory=list)
    vm_series: list[str] = Field(default_factory=list)
    attestation_supported: bool = False


class ConfidentialOptionsListResponse(BaseModel):
    """List of confidential computing options."""

    options: list[ConfidentialOptionResponse] = Field(default_factory=list)
    total: int = 0


class ConfidentialVmSkuResponse(BaseModel):
    """A confidential computing VM SKU."""

    name: str
    series: str
    vcpus: int
    memory_gb: int
    tee_type: str
    vendor: str
    max_data_disks: int = 0
    enclave_memory_mb: int | None = None
    description: str = ""


class ConfidentialVmSkuListResponse(BaseModel):
    """List of confidential VM SKUs."""

    skus: list[ConfidentialVmSkuResponse] = Field(default_factory=list)
    total: int = 0


class ConfidentialRegionResponse(BaseModel):
    """A region with confidential computing support."""

    name: str
    display_name: str
    tee_types: list[str] = Field(default_factory=list)
    services: list[str] = Field(default_factory=list)


class ConfidentialRegionListResponse(BaseModel):
    """List of regions with confidential computing support."""

    regions: list[ConfidentialRegionResponse] = Field(default_factory=list)
    total: int = 0


# ── Request Schemas ──────────────────────────────────────────────────────────


class ConfidentialRecommendRequest(BaseModel):
    """Request body for confidential computing recommendation."""

    workload_type: str = Field(
        ..., description="Workload type: web_app, database, container, ledger, multi_party"
    )
    requirements: dict = Field(
        default_factory=dict,
        description="Optional requirements: min_vcpus, min_memory_gb, tee_preference, region",
    )


class ConfidentialRecommendResponse(BaseModel):
    """Recommendation result for confidential computing."""

    workload_type: str
    recommended_option: dict = Field(default_factory=dict)
    recommended_skus: list[dict] = Field(default_factory=list)
    region_options: list[dict] = Field(default_factory=list)
    attestation: dict | None = None
    rationale: str = ""


class ConfidentialArchitectureRequest(BaseModel):
    """Request body for confidential architecture overlay."""

    base_architecture: dict = Field(
        ..., description="Base landing zone architecture to enhance"
    )
    cc_options: dict = Field(
        ...,
        description=(
            "CC configuration: cc_type, vm_sku, region, enable_attestation"
        ),
    )


class ConfidentialArchitectureResponse(BaseModel):
    """Enhanced architecture with confidential computing overlay."""

    architecture: dict = Field(default_factory=dict)
    cc_enabled: bool = True


class ConfidentialBicepRequest(BaseModel):
    """Request body for generating confidential Bicep templates."""

    template_type: str = Field(
        ...,
        description=(
            "Template type: confidential_vm, confidential_aks,"
            " attestation_provider, confidential_sql, full_stack"
        ),
    )
    config: dict = Field(
        default_factory=dict, description="Template configuration parameters"
    )


class ConfidentialBicepResponse(BaseModel):
    """Generated Bicep template response."""

    template_type: str
    bicep_template: str = ""
    description: str = ""


class AttestationConfigResponse(BaseModel):
    """Attestation configuration for a CC type."""

    cc_type: str
    attestation_provider: str = ""
    protocol: str = ""
    evidence_type: str = ""
    key_release_policy: str = ""
    steps: list[str] = Field(default_factory=list)
