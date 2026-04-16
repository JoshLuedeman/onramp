"""Schemas for AI output validation results and metrics."""

from enum import Enum

from pydantic import BaseModel, Field


class AIOutputType(str, Enum):
    """Types of AI outputs that can be validated."""

    architecture = "architecture"
    policy = "policy"
    sku_recommendation = "sku_recommendation"
    security_finding = "security_finding"
    compliance_gap = "compliance_gap"


class ValidationError(BaseModel):
    """A single validation error."""

    field: str
    message: str
    expected: str | None = None
    received: str | None = None


class ValidationResult(BaseModel):
    """Result of validating an AI output."""

    success: bool
    errors: list[ValidationError] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    validated_data: dict | None = None


class ValidationMetrics(BaseModel):
    """Validation pass/fail metrics for a specific feature."""

    feature: str
    total_validations: int = 0
    passed: int = 0
    failed: int = 0
    failure_rate: float = 0.0
    common_errors: list[str] = Field(default_factory=list)


class AzureResourceType(BaseModel):
    """Known valid Azure resource types."""

    VALID_TYPES: list[str] = Field(default_factory=lambda: [
        "Microsoft.Compute/virtualMachines",
        "Microsoft.Compute/virtualMachineScaleSets",
        "Microsoft.Compute/disks",
        "Microsoft.Compute/availabilitySets",
        "Microsoft.Network/virtualNetworks",
        "Microsoft.Network/networkSecurityGroups",
        "Microsoft.Network/loadBalancers",
        "Microsoft.Network/applicationGateways",
        "Microsoft.Network/publicIPAddresses",
        "Microsoft.Network/networkInterfaces",
        "Microsoft.Network/privateDnsZones",
        "Microsoft.Network/privateEndpoints",
        "Microsoft.Network/azureFirewalls",
        "Microsoft.Network/bastionHosts",
        "Microsoft.Network/virtualNetworkGateways",
        "Microsoft.Network/expressRouteCircuits",
        "Microsoft.Network/frontDoors",
        "Microsoft.Network/trafficManagerProfiles",
        "Microsoft.Storage/storageAccounts",
        "Microsoft.Sql/servers",
        "Microsoft.Sql/servers/databases",
        "Microsoft.DBforPostgreSQL/flexibleServers",
        "Microsoft.DBforMySQL/flexibleServers",
        "Microsoft.DocumentDB/databaseAccounts",
        "Microsoft.Cache/redis",
        "Microsoft.Web/sites",
        "Microsoft.Web/serverFarms",
        "Microsoft.App/containerApps",
        "Microsoft.App/managedEnvironments",
        "Microsoft.ContainerRegistry/registries",
        "Microsoft.ContainerService/managedClusters",
        "Microsoft.KeyVault/vaults",
        "Microsoft.ManagedIdentity/userAssignedIdentities",
        "Microsoft.Authorization/roleAssignments",
        "Microsoft.Authorization/policyAssignments",
        "Microsoft.Authorization/policyDefinitions",
        "Microsoft.Management/managementGroups",
        "Microsoft.Resources/resourceGroups",
        "Microsoft.OperationalInsights/workspaces",
        "Microsoft.Insights/components",
        "Microsoft.Insights/actionGroups",
        "Microsoft.Insights/metricAlerts",
        "Microsoft.Insights/diagnosticSettings",
        "Microsoft.Security/pricings",
        "Microsoft.SecurityInsights/onboardingStates",
        "Microsoft.RecoveryServices/vaults",
        "Microsoft.CognitiveServices/accounts",
        "Microsoft.MachineLearningServices/workspaces",
        "Microsoft.EventHub/namespaces",
        "Microsoft.ServiceBus/namespaces",
        "Microsoft.Logic/workflows",
        "Microsoft.Functions/functionApps",
    ])


class AzureRegion(BaseModel):
    """Known valid Azure regions."""

    VALID_REGIONS: list[str] = Field(default_factory=lambda: [
        "eastus",
        "eastus2",
        "westus",
        "westus2",
        "westus3",
        "centralus",
        "northcentralus",
        "southcentralus",
        "westcentralus",
        "canadacentral",
        "canadaeast",
        "brazilsouth",
        "northeurope",
        "westeurope",
        "uksouth",
        "ukwest",
        "francecentral",
        "francesouth",
        "germanywestcentral",
        "germanynorth",
        "switzerlandnorth",
        "switzerlandwest",
        "norwayeast",
        "norwaywest",
        "swedencentral",
        "polandcentral",
        "italynorth",
        "spaincentral",
        "australiaeast",
        "australiasoutheast",
        "australiacentral",
        "eastasia",
        "southeastasia",
        "japaneast",
        "japanwest",
        "koreacentral",
        "koreasouth",
        "centralindia",
        "southindia",
        "westindia",
        "uaenorth",
        "uaecentral",
        "southafricanorth",
        "southafricawest",
        "qatarcentral",
        "israelcentral",
        "mexicocentral",
        "newzealandnorth",
    ])


class AzureSKU(BaseModel):
    """Known valid Azure VM SKU families."""

    VALID_SKU_FAMILIES: list[str] = Field(default_factory=lambda: [
        "Standard_A",
        "Standard_B",
        "Standard_D",
        "Standard_DC",
        "Standard_DS",
        "Standard_Dv2",
        "Standard_DSv2",
        "Standard_Dv3",
        "Standard_DSv3",
        "Standard_Dv4",
        "Standard_DSv4",
        "Standard_Dv5",
        "Standard_DSv5",
        "Standard_Dav4",
        "Standard_Dasv4",
        "Standard_Dav5",
        "Standard_Dasv5",
        "Standard_Ddv4",
        "Standard_Ddsv4",
        "Standard_Ddv5",
        "Standard_Ddsv5",
        "Standard_Dplsv5",
        "Standard_Dpldsv5",
        "Standard_E",
        "Standard_Ev3",
        "Standard_ESv3",
        "Standard_Ev4",
        "Standard_ESv4",
        "Standard_Ev5",
        "Standard_ESv5",
        "Standard_Eav4",
        "Standard_Easv4",
        "Standard_Eav5",
        "Standard_Easv5",
        "Standard_Edv4",
        "Standard_Edsv4",
        "Standard_Edv5",
        "Standard_Edsv5",
        "Standard_F",
        "Standard_FS",
        "Standard_Fv2",
        "Standard_FSv2",
        "Standard_G",
        "Standard_GS",
        "Standard_H",
        "Standard_HB",
        "Standard_HC",
        "Standard_L",
        "Standard_Lv2",
        "Standard_Lsv2",
        "Standard_Lsv3",
        "Standard_Lasv3",
        "Standard_M",
        "Standard_MS",
        "Standard_Mv2",
        "Standard_MSv2",
        "Standard_NC",
        "Standard_NCv2",
        "Standard_NCv3",
        "Standard_NCSv3",
        "Standard_NCasT4_v3",
        "Standard_NV",
        "Standard_NVv3",
        "Standard_NVv4",
        "Standard_NVadsA10_v5",
        "Standard_ND",
        "Standard_NDv2",
        "Standard_NP",
    ])
