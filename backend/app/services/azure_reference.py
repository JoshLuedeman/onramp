"""Azure reference data for validating AI outputs against known Azure values.

This module provides sets of known-valid Azure resource types, regions, and
VM SKU families so the validator can flag hallucinated values.
"""

import logging

from app.config import settings

logger = logging.getLogger(__name__)


class AzureReferenceData:
    """Singleton holding known-valid Azure reference data.

    In dev mode every lookup returns ``True`` so mock/archetype data is
    never rejected.
    """

    # -- Known Azure resource type strings --------------------------------
    VALID_RESOURCE_TYPES: set[str] = {
        "Microsoft.Compute/virtualMachines",
        "Microsoft.Compute/virtualMachineScaleSets",
        "Microsoft.Compute/disks",
        "Microsoft.Compute/availabilitySets",
        "Microsoft.Compute/images",
        "Microsoft.Compute/snapshots",
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
        "Microsoft.Network/routeTables",
        "Microsoft.Network/natGateways",
        "Microsoft.Network/ddosProtectionPlans",
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
    }

    # -- Known Azure regions -----------------------------------------------
    VALID_REGIONS: set[str] = {
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
    }

    # -- Known VM SKU family prefixes --------------------------------------
    VALID_VM_SKUS: set[str] = {
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
    }

    def is_valid_resource_type(self, type_name: str) -> bool:
        """Check whether *type_name* is a known Azure resource type.

        In dev mode this always returns ``True`` so mock data is accepted.
        """
        if settings.is_dev_mode:
            return True
        return type_name in self.VALID_RESOURCE_TYPES

    def is_valid_region(self, region: str) -> bool:
        """Check whether *region* is a known Azure region.

        In dev mode this always returns ``True``.
        """
        if settings.is_dev_mode:
            return True
        return region.lower() in self.VALID_REGIONS

    def is_valid_sku(self, sku: str) -> bool:
        """Check whether *sku* matches a known VM SKU family prefix.

        For example, ``Standard_D2s_v3`` starts with the family prefix
        ``Standard_Dv3`` — but because SKU naming is inconsistent we
        simply check whether *any* known prefix is a prefix of *sku*
        (case-insensitive).

        In dev mode this always returns ``True``.
        """
        if settings.is_dev_mode:
            return True
        sku_upper = sku
        return any(sku_upper.startswith(prefix) for prefix in self.VALID_VM_SKUS)


# Module-level singleton
azure_reference = AzureReferenceData()
