"""Pulumi code generator — creates deployable Pulumi programs from architecture definitions."""

import json
import logging
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger(__name__)

PulumiLanguage = Literal["typescript", "python"]

SUPPORTED_LANGUAGES: list[PulumiLanguage] = ["typescript", "python"]

PULUMI_TEMPLATES: list[dict] = [
    {
        "name": "azure-landing-zone",
        "description": "Full Azure landing zone with management groups, networking, and governance",
        "languages": ["typescript", "python"],
    },
    {
        "name": "hub-spoke-network",
        "description": "Hub-spoke network topology with Azure Firewall and Bastion",
        "languages": ["typescript", "python"],
    },
    {
        "name": "policy-governance",
        "description": "Azure Policy assignments and governance controls",
        "languages": ["typescript", "python"],
    },
]


class PulumiGenerator:
    """Generates Pulumi programs from architecture definitions.

    Supports TypeScript and Python output languages. In dev mode returns realistic
    mock Pulumi code with Azure Native provider configuration.
    """

    def __init__(self):
        self.ai_generated: bool = False

    def get_version(self) -> str:
        """Return the current generator version."""
        return "1.0.0"

    def list_templates(self) -> list[dict]:
        """List all available Pulumi templates."""
        return list(PULUMI_TEMPLATES)

    def validate_language(self, language: str) -> PulumiLanguage:
        """Validate and return the requested language.

        Args:
            language: The language string to validate.

        Returns:
            The validated PulumiLanguage literal.

        Raises:
            ValueError: If language is not supported.
        """
        if language not in SUPPORTED_LANGUAGES:
            raise ValueError(
                f"Unsupported language '{language}'. "
                f"Supported: {', '.join(SUPPORTED_LANGUAGES)}"
            )
        return language  # type: ignore[return-value]

    async def generate_from_architecture_with_ai(
        self,
        architecture: dict,
        language: PulumiLanguage = "typescript",
    ) -> dict[str, str]:
        """Generate Pulumi files using AI, falling back to static generation.

        Args:
            architecture: The architecture definition dict.
            language: Target language — 'typescript' or 'python'.

        Returns:
            A dict mapping filename to file content.
        """
        from app.services.ai_foundry import ai_client

        static_files = self.generate_from_architecture(architecture, language)

        try:
            raw_response = await ai_client.generate_pulumi(architecture, language)
            ai_files = json.loads(raw_response)
            if not isinstance(ai_files, dict) or not ai_files:
                raise ValueError("AI response is not a valid file mapping")
            static_files.update(ai_files)
            self.ai_generated = True
            logger.info("Pulumi %s generated via AI (%d files)", language, len(ai_files))
        except (json.JSONDecodeError, ValueError, TypeError) as e:
            logger.warning("AI Pulumi generation failed, using static fallback: %s", e)
            self.ai_generated = False

        return static_files

    def generate_from_architecture(
        self,
        architecture: dict,
        language: PulumiLanguage = "typescript",
    ) -> dict[str, str]:
        """Generate a set of Pulumi files from an architecture definition.

        Args:
            architecture: The architecture definition dict.
            language: Target language — 'typescript' or 'python'.

        Returns:
            A dict mapping filename to file content.
        """
        language = self.validate_language(language)
        if language == "typescript":
            return self._generate_typescript(architecture)
        return self._generate_python(architecture)

    # ------------------------------------------------------------------
    # TypeScript generation
    # ------------------------------------------------------------------

    def _generate_typescript(self, architecture: dict) -> dict[str, str]:
        """Generate TypeScript Pulumi program files."""
        files: dict[str, str] = {}

        project_name = self._project_name(architecture)
        region = self._primary_region(architecture)

        files["Pulumi.yaml"] = self._pulumi_yaml(project_name, "nodejs")
        files["package.json"] = self._ts_package_json(project_name)
        files["tsconfig.json"] = self._tsconfig()
        files["index.ts"] = self._ts_index(architecture, region)

        return files

    def _ts_package_json(self, project_name: str) -> str:
        """Generate package.json for the TypeScript Pulumi project."""
        pkg = {
            "name": project_name,
            "version": "1.0.0",
            "description": "Azure Landing Zone — generated by OnRamp",
            "main": "index.ts",
            "devDependencies": {
                "@types/node": "^20",
                "typescript": "^5.0",
            },
            "dependencies": {
                "@pulumi/pulumi": "^3.0.0",
                "@pulumi/azure-native": "^2.0.0",
            },
        }
        return json.dumps(pkg, indent=2) + "\n"

    def _tsconfig(self) -> str:
        """Generate tsconfig.json for the Pulumi project."""
        cfg = {
            "compilerOptions": {
                "strict": True,
                "outDir": "bin",
                "target": "es2020",
                "module": "commonjs",
                "moduleResolution": "node",
                "sourceMap": True,
                "experimentalDecorators": True,
                "pretty": True,
                "noFallthroughCasesInSwitch": True,
                "noImplicitReturns": True,
                "forceConsistentCasingInFileNames": True,
            },
            "files": ["index.ts"],
        }
        return json.dumps(cfg, indent=2) + "\n"

    def _ts_index(self, architecture: dict, region: str) -> str:
        """Generate the main index.ts entry point."""
        org_size = architecture.get("organization_size", "medium")
        hub_cidr = (
            architecture.get("network_topology", {})
            .get("hub", {})
            .get("vnet_cidr", "10.0.0.0/16")
        )
        enable_firewall = architecture.get("security", {}).get("azure_firewall", True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        lines = [
            f"// OnRamp Generated — v{self.get_version()} — {timestamp}",
            'import * as pulumi from "@pulumi/pulumi";',
            'import * as azure_native from "@pulumi/azure-native";',
            "",
            "// ---------------------",
            "// Configuration",
            "// ---------------------",
            "const config = new pulumi.Config();",
            f'const location = config.get("location") || "{region}";',
            'const environment = config.get("environment") || "prod";',
            "",
            "const tags = {",
            '    managedBy: "OnRamp",',
            f'    organizationSize: "{org_size}",',
            "    environment,",
            "};",
            "",
            "// ---------------------",
            "// Resource Groups",
            "// ---------------------",
            'const rgPlatform = new azure_native.resources.ResourceGroup("rg-platform", {',
            "    resourceGroupName: `rg-platform-${environment}`,",
            "    location,",
            "    tags,",
            "});",
            "",
            'const rgNetworking = new azure_native.resources.ResourceGroup("rg-networking", {',
            "    resourceGroupName: `rg-networking-${environment}`,",
            "    location,",
            "    tags,",
            "});",
            "",
            'const rgSecurity = new azure_native.resources.ResourceGroup("rg-security", {',
            "    resourceGroupName: `rg-security-${environment}`,",
            "    location,",
            "    tags,",
            "});",
            "",
            "// ---------------------",
            "// Hub Virtual Network",
            "// ---------------------",
            'const hubVnet = new azure_native.network.VirtualNetwork("vnet-hub", {',
            "    resourceGroupName: rgNetworking.name,",
            "    location,",
            "    addressSpace: {",
            f'        addressPrefixes: ["{hub_cidr}"],',
            "    },",
            "    tags,",
            "});",
            "",
        ]

        # Azure Firewall
        if enable_firewall:
            lines.extend([
                "// ---------------------",
                "// Azure Firewall",
                "// ---------------------",
                'const fwSubnet = new azure_native.network.Subnet("AzureFirewallSubnet", {',
                "    resourceGroupName: rgNetworking.name,",
                "    virtualNetworkName: hubVnet.name,",
                '    subnetName: "AzureFirewallSubnet",',
                '    addressPrefix: "10.0.1.0/26",',
                "});",
                "",
                "const fwPublicIp = new azure_native.network.PublicIPAddress("
                '"fw-pip", {',
                "    resourceGroupName: rgNetworking.name,",
                "    location,",
                '    sku: { name: "Standard" },',
                '    publicIPAllocationMethod: "Static",',
                "    tags,",
                "});",
                "",
                'const firewall = new azure_native.network.AzureFirewall("fw-hub", {',
                "    resourceGroupName: rgNetworking.name,",
                "    location,",
                "    ipConfigurations: [{",
                '        name: "fw-config",',
                "        subnet: { id: fwSubnet.id },",
                "        publicIPAddress: { id: fwPublicIp.id },",
                "    }],",
                "    tags,",
                "});",
                "",
            ])

        # Spokes
        spokes = architecture.get("network_topology", {}).get("spokes", [])
        for i, spoke in enumerate(spokes):
            spoke_name = spoke.get("name", f"spoke-{i}")
            spoke_cidr = spoke.get("vnet_cidr", f"10.{i + 1}.0.0/16")
            lines.extend([
                "// ---------------------",
                f"// Spoke: {spoke_name}",
                "// ---------------------",
                f'const spoke{i}Vnet = new azure_native.network.VirtualNetwork('
                f'"vnet-{spoke_name}", {{',
                "    resourceGroupName: rgNetworking.name,",
                "    location,",
                "    addressSpace: {",
                f'        addressPrefixes: ["{spoke_cidr}"],',
                "    },",
                "    tags,",
                "});",
                "",
                f'const peering{i}HubToSpoke = new azure_native.network.VirtualNetworkPeering('
                f'"hub-to-{spoke_name}", {{',
                "    resourceGroupName: rgNetworking.name,",
                "    virtualNetworkName: hubVnet.name,",
                f"    remoteVirtualNetwork: {{ id: spoke{i}Vnet.id }},",
                "    allowVirtualNetworkAccess: true,",
                "    allowForwardedTraffic: true,",
                "});",
                "",
            ])

        # Exports
        lines.extend([
            "// ---------------------",
            "// Stack Exports",
            "// ---------------------",
            "export const platformResourceGroupName = rgPlatform.name;",
            "export const networkingResourceGroupName = rgNetworking.name;",
            "export const hubVnetId = hubVnet.id;",
        ])

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Python generation
    # ------------------------------------------------------------------

    def _generate_python(self, architecture: dict) -> dict[str, str]:
        """Generate Python Pulumi program files."""
        files: dict[str, str] = {}

        project_name = self._project_name(architecture)
        region = self._primary_region(architecture)

        files["Pulumi.yaml"] = self._pulumi_yaml(project_name, "python")
        files["requirements.txt"] = self._py_requirements()
        files["__main__.py"] = self._py_main(architecture, region)

        return files

    def _py_requirements(self) -> str:
        """Generate requirements.txt for the Python Pulumi project."""
        return "pulumi>=3.0.0,<4.0.0\npulumi-azure-native>=2.0.0,<3.0.0\n"

    def _py_main(self, architecture: dict, region: str) -> str:
        """Generate the main __main__.py entry point."""
        org_size = architecture.get("organization_size", "medium")
        hub_cidr = (
            architecture.get("network_topology", {})
            .get("hub", {})
            .get("vnet_cidr", "10.0.0.0/16")
        )
        enable_firewall = architecture.get("security", {}).get("azure_firewall", True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        lines = [
            f'"""OnRamp Generated — v{self.get_version()} — {timestamp}"""',
            "",
            "import pulumi",
            "import pulumi_azure_native as azure_native",
            "",
            "# ---------------------",
            "# Configuration",
            "# ---------------------",
            "config = pulumi.Config()",
            f'location = config.get("location") or "{region}"',
            'environment = config.get("environment") or "prod"',
            "",
            "tags = {",
            '    "managedBy": "OnRamp",',
            f'    "organizationSize": "{org_size}",',
            '    "environment": environment,',
            "}",
            "",
            "# ---------------------",
            "# Resource Groups",
            "# ---------------------",
            'rg_platform = azure_native.resources.ResourceGroup("rg-platform",',
            '    resource_group_name=f"rg-platform-{environment}",',
            "    location=location,",
            "    tags=tags,",
            ")",
            "",
            'rg_networking = azure_native.resources.ResourceGroup("rg-networking",',
            '    resource_group_name=f"rg-networking-{environment}",',
            "    location=location,",
            "    tags=tags,",
            ")",
            "",
            'rg_security = azure_native.resources.ResourceGroup("rg-security",',
            '    resource_group_name=f"rg-security-{environment}",',
            "    location=location,",
            "    tags=tags,",
            ")",
            "",
            "# ---------------------",
            "# Hub Virtual Network",
            "# ---------------------",
            'hub_vnet = azure_native.network.VirtualNetwork("vnet-hub",',
            "    resource_group_name=rg_networking.name,",
            "    location=location,",
            "    address_space=azure_native.network.AddressSpaceArgs(",
            f'        address_prefixes=["{hub_cidr}"],',
            "    ),",
            "    tags=tags,",
            ")",
            "",
        ]

        # Azure Firewall
        if enable_firewall:
            lines.extend([
                "# ---------------------",
                "# Azure Firewall",
                "# ---------------------",
                'fw_subnet = azure_native.network.Subnet("AzureFirewallSubnet",',
                "    resource_group_name=rg_networking.name,",
                "    virtual_network_name=hub_vnet.name,",
                '    subnet_name="AzureFirewallSubnet",',
                '    address_prefix="10.0.1.0/26",',
                ")",
                "",
                'fw_public_ip = azure_native.network.PublicIPAddress("fw-pip",',
                "    resource_group_name=rg_networking.name,",
                "    location=location,",
                '    sku=azure_native.network.PublicIPAddressSkuArgs(name="Standard"),',
                '    public_ip_allocation_method="Static",',
                "    tags=tags,",
                ")",
                "",
                'firewall = azure_native.network.AzureFirewall("fw-hub",',
                "    resource_group_name=rg_networking.name,",
                "    location=location,",
                "    ip_configurations=[azure_native.network.AzureFirewallIPConfigurationArgs(",
                '        name="fw-config",',
                "        subnet=azure_native.network.SubResourceArgs(id=fw_subnet.id),",
                "        public_ip_address=azure_native.network.SubResourceArgs("
                "id=fw_public_ip.id),",
                "    )],",
                "    tags=tags,",
                ")",
                "",
            ])

        # Spokes
        spokes = architecture.get("network_topology", {}).get("spokes", [])
        for i, spoke in enumerate(spokes):
            spoke_name = spoke.get("name", f"spoke-{i}")
            spoke_cidr = spoke.get("vnet_cidr", f"10.{i + 1}.0.0/16")
            lines.extend([
                "# ---------------------",
                f"# Spoke: {spoke_name}",
                "# ---------------------",
                f'spoke{i}_vnet = azure_native.network.VirtualNetwork("vnet-{spoke_name}",',
                "    resource_group_name=rg_networking.name,",
                "    location=location,",
                "    address_space=azure_native.network.AddressSpaceArgs(",
                f'        address_prefixes=["{spoke_cidr}"],',
                "    ),",
                "    tags=tags,",
                ")",
                "",
                f'peering{i}_hub_to_spoke = azure_native.network.VirtualNetworkPeering('
                f'"hub-to-{spoke_name}",',
                "    resource_group_name=rg_networking.name,",
                "    virtual_network_name=hub_vnet.name,",
                f"    remote_virtual_network=azure_native.network.SubResourceArgs("
                f"id=spoke{i}_vnet.id),",
                "    allow_virtual_network_access=True,",
                "    allow_forwarded_traffic=True,",
                ")",
                "",
            ])

        # Exports
        lines.extend([
            "# ---------------------",
            "# Stack Exports",
            "# ---------------------",
            'pulumi.export("platform_resource_group_name", rg_platform.name)',
            'pulumi.export("networking_resource_group_name", rg_networking.name)',
            'pulumi.export("hub_vnet_id", hub_vnet.id)',
        ])

        return "\n".join(lines) + "\n"

    # ------------------------------------------------------------------
    # Shared helpers
    # ------------------------------------------------------------------

    def _pulumi_yaml(self, project_name: str, runtime: str) -> str:
        """Generate the Pulumi.yaml project file."""
        lines = [
            f"name: {project_name}",
            "description: Azure Landing Zone — generated by OnRamp",
            f"runtime: {runtime}",
            "config:",
            "  azure-native:location:",
            "    default: eastus2",
        ]
        return "\n".join(lines) + "\n"

    def _project_name(self, architecture: dict) -> str:
        """Derive a project name from the architecture."""
        org = architecture.get("organization_size", "org")
        return f"onramp-landing-zone-{org}"

    def _primary_region(self, architecture: dict) -> str:
        """Extract the primary Azure region from the architecture."""
        return (
            architecture.get("network_topology", {}).get("primary_region", "eastus2")
        )


# Singleton
pulumi_generator = PulumiGenerator()
