"""Pydantic validation models for AI-generated outputs.

These models mirror the JSON schemas defined in prompts.py and are used
by the AI validator to check structural correctness of AI responses.
"""

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# Architecture Output
# ---------------------------------------------------------------------------

class ManagementGroupNode(BaseModel):
    """A node in the management group hierarchy."""

    display_name: str
    children: dict[str, "ManagementGroupNode"] = Field(default_factory=dict)


class Subscription(BaseModel):
    """An Azure subscription entry."""

    name: str
    purpose: str
    management_group: str
    budget_usd: int | float = 0


class NetworkTopology(BaseModel):
    """Network topology configuration."""

    type: str  # "hub-spoke" or "vwan"
    primary_region: str = ""


class Identity(BaseModel):
    """Identity and access management configuration."""

    provider: str = ""
    rbac_model: str = ""
    pim_enabled: bool = False
    conditional_access: bool = False
    mfa_policy: str = ""


class SecurityConfig(BaseModel):
    """Security configuration."""

    defender_for_cloud: bool = False
    defender_plans: list[str] = Field(default_factory=list)
    sentinel: bool = False
    ddos_protection: bool = False
    azure_firewall: bool = False
    waf: bool = False
    key_vault_per_subscription: bool = False


class GovernancePolicy(BaseModel):
    """A governance policy definition."""

    name: str
    scope: str = ""
    effect: str = ""
    description: str = ""


class TaggingStrategy(BaseModel):
    """Resource tagging strategy."""

    mandatory_tags: list[str] = Field(default_factory=list)
    optional_tags: list[str] = Field(default_factory=list)


class CostManagement(BaseModel):
    """Cost management settings."""

    budgets_enabled: bool = False
    alerts_enabled: bool = False
    optimization_recommendations: bool = False


class Governance(BaseModel):
    """Governance configuration."""

    policies: list[GovernancePolicy] = Field(default_factory=list)
    tagging_strategy: TaggingStrategy = Field(default_factory=TaggingStrategy)
    naming_convention: str = ""
    cost_management: CostManagement = Field(default_factory=CostManagement)


class Management(BaseModel):
    """Operations management configuration."""

    log_analytics: dict = Field(default_factory=dict)
    monitoring: dict = Field(default_factory=dict)
    backup: dict = Field(default_factory=dict)
    update_management: bool = False


class ComplianceFramework(BaseModel):
    """Compliance framework assessment."""

    name: str
    controls_applied: int = 0
    coverage_percent: int | float = 0


class PlatformAutomation(BaseModel):
    """Platform automation settings."""

    iac_tool: str = ""
    cicd_platform: str = ""
    repo_structure: str = ""


class ArchitectureOutput(BaseModel):
    """Full architecture output matching the prompts.py JSON schema."""

    organization_size: str
    management_groups: dict = Field(default_factory=dict)
    subscriptions: list[Subscription] = Field(default_factory=list)
    network_topology: NetworkTopology | dict = Field(default_factory=dict)
    identity: Identity | dict = Field(default_factory=dict)
    security: SecurityConfig | dict = Field(default_factory=dict)
    governance: Governance | dict = Field(default_factory=dict)
    management: Management | dict = Field(default_factory=dict)
    compliance_frameworks: list[ComplianceFramework] = Field(default_factory=list)
    platform_automation: PlatformAutomation | dict = Field(default_factory=dict)
    recommendations: list[str] = Field(default_factory=list)
    estimated_monthly_cost_usd: int | float = 0

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Policy Definition Output
# ---------------------------------------------------------------------------

class PolicyDefinitionOutput(BaseModel):
    """Azure Policy definition output."""

    name: str
    display_name: str = ""
    description: str = ""
    mode: str = "All"
    policy_rule: dict = Field(default_factory=dict)
    parameters: dict = Field(default_factory=dict)

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# SKU Recommendation Output
# ---------------------------------------------------------------------------

class SKURecommendationOutput(BaseModel):
    """VM SKU recommendation output."""

    workload: str
    recommended_sku: str
    reasoning: str = ""
    monthly_cost_estimate: int | float = 0

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Security Finding Output
# ---------------------------------------------------------------------------

class SecurityFindingOutput(BaseModel):
    """Security finding output."""

    severity: str
    category: str
    resource: str
    finding: str
    remediation: str = ""

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Compliance Gap Output
# ---------------------------------------------------------------------------

class ComplianceGapOutput(BaseModel):
    """Compliance gap analysis output."""

    framework: str
    control_id: str
    status: str
    gap_description: str
    remediation: str = ""

    model_config = {"extra": "allow"}
