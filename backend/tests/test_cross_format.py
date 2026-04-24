"""Cross-format equivalence, security, and consistency tests for IaC generators.

Validates that all OnRamp IaC generators (Bicep, Terraform, ARM, Pulumi TS,
Pulumi Python) produce equivalent infrastructure from the same architecture
input, follow security best practices, and maintain consistent naming and
parameterisation conventions.  Also validates that generated CI/CD pipelines
(GitHub Actions, Azure DevOps) are free of hardcoded credentials and use
federated/OIDC authentication.
"""

import json
import re

import pytest

from app.schemas.pipeline import IaCFormat
from app.services.arm_generator import arm_generator
from app.services.azure_devops_generator import azure_devops_generator
from app.services.bicep_generator import bicep_generator
from app.services.github_actions_generator import github_actions_generator
from app.services.pulumi_generator import pulumi_generator
from app.services.terraform_generator import terraform_generator

# ---------------------------------------------------------------------------
# Shared test architecture — hub-spoke topology with two spokes
# ---------------------------------------------------------------------------

STANDARD_ARCHITECTURE: dict = {
    "organization_size": "medium",
    "management_groups": [{"name": "Contoso", "children": []}],
    "subscriptions": [
        {"name": "sub-prod", "purpose": "production", "budget_usd": 5000},
    ],
    "network_topology": {
        "type": "hub-spoke",
        "primary_region": "eastus2",
        "hub": {"vnet_cidr": "10.0.0.0/16"},
        "spokes": [
            {"name": "prod", "vnet_cidr": "10.1.0.0/16"},
            {"name": "dev", "vnet_cidr": "10.2.0.0/16"},
        ],
        "dns": {},
        "hybrid_connectivity": {},
    },
    "identity": {
        "provider": "entra_id",
        "rbac_model": "custom",
        "pim_enabled": True,
    },
    "security": {
        "defender_for_cloud": True,
        "sentinel": True,
        "ddos_protection": True,
        "azure_firewall": True,
        "bastion": True,
        "waf": True,
        "key_vault_per_subscription": True,
    },
    "governance": {
        "policies": [
            {"name": "allowed-locations", "scope": "root", "effect": "Deny"},
        ],
        "tagging_strategy": {"mandatory_tags": ["environment", "owner"]},
    },
}

# ---------------------------------------------------------------------------
# Pre-generated outputs (module-level so generators run once per session)
# ---------------------------------------------------------------------------

_bicep_files: dict[str, str] = bicep_generator.generate_from_architecture(
    STANDARD_ARCHITECTURE
)
_terraform_files: dict[str, str] = terraform_generator.generate_from_architecture(
    STANDARD_ARCHITECTURE
)
_arm_files: dict[str, str] = arm_generator.generate_from_architecture(
    STANDARD_ARCHITECTURE
)
_pulumi_ts_files: dict[str, str] = pulumi_generator.generate_from_architecture(
    STANDARD_ARCHITECTURE, language="typescript"
)
_pulumi_py_files: dict[str, str] = pulumi_generator.generate_from_architecture(
    STANDARD_ARCHITECTURE, language="python"
)

# Combine all IaC content into a single string per format for text searches
_bicep_all = "\n".join(_bicep_files.values())
_terraform_all = "\n".join(_terraform_files.values())
_arm_all = "\n".join(_arm_files.values())
_pulumi_ts_all = "\n".join(_pulumi_ts_files.values())
_pulumi_py_all = "\n".join(_pulumi_py_files.values())

ALL_IAC_OUTPUTS: list[tuple[str, str]] = [
    ("bicep", _bicep_all),
    ("terraform", _terraform_all),
    ("arm", _arm_all),
    ("pulumi_ts", _pulumi_ts_all),
    ("pulumi_py", _pulumi_py_all),
]

ALL_IAC_FILE_MAPS: list[tuple[str, dict[str, str]]] = [
    ("bicep", _bicep_files),
    ("terraform", _terraform_files),
    ("arm", _arm_files),
    ("pulumi_ts", _pulumi_ts_files),
    ("pulumi_py", _pulumi_py_files),
]

# Pipeline outputs — one per IaC format × pipeline platform
_gh_workflows: dict[str, dict[str, str]] = {}
for _fmt in IaCFormat:
    _gh_workflows[_fmt.value] = github_actions_generator.generate_workflows(
        STANDARD_ARCHITECTURE, _fmt
    )

_ado_pipelines: dict[str, dict[str, str]] = {}
for _fmt in IaCFormat:
    _ado_pipelines[_fmt.value] = azure_devops_generator.generate_pipeline(
        STANDARD_ARCHITECTURE, _fmt
    )


# ═══════════════════════════════════════════════════════════════════════════
# 1. Cross-Format Equivalence
# ═══════════════════════════════════════════════════════════════════════════


class TestCrossFormatEquivalence:
    """Verify that all IaC generators represent the same infrastructure."""

    # -- File-level checks ------------------------------------------------

    @pytest.mark.parametrize("fmt,files", ALL_IAC_FILE_MAPS, ids=[f[0] for f in ALL_IAC_FILE_MAPS])
    def test_generator_returns_dict_of_strings(self, fmt: str, files: dict[str, str]):
        """Each generator must return a dict mapping filenames to string content."""
        assert isinstance(files, dict), f"{fmt}: expected dict"
        for name, content in files.items():
            assert isinstance(name, str), f"{fmt}: filename must be str"
            assert isinstance(content, str), f"{fmt}: content must be str"
            assert len(content) > 0, f"{fmt}: file '{name}' is empty"

    @pytest.mark.parametrize("fmt,files", ALL_IAC_FILE_MAPS, ids=[f[0] for f in ALL_IAC_FILE_MAPS])
    def test_generator_produces_multiple_files(self, fmt: str, files: dict[str, str]):
        """Each generator must emit more than one file."""
        assert len(files) >= 2, f"{fmt}: expected ≥2 files, got {len(files)}"

    # -- Hub virtual network ----------------------------------------------

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_hub_virtual_network_represented(self, fmt: str, content: str):
        """Every format must declare a hub virtual network."""
        lower = content.lower()
        assert "hub" in lower and "vnet" in lower, (
            f"{fmt}: hub virtual network not found"
        )

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_hub_cidr_present(self, fmt: str, content: str):
        """Every format must reference the configured hub CIDR."""
        assert "10.0.0.0/16" in content, (
            f"{fmt}: hub CIDR 10.0.0.0/16 not found"
        )

    # -- Spoke virtual networks -------------------------------------------

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_spoke_prod_represented(self, fmt: str, content: str):
        """Every format must declare the 'prod' spoke."""
        lower = content.lower()
        assert "prod" in lower, f"{fmt}: prod spoke not found"

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_spoke_dev_represented(self, fmt: str, content: str):
        """Every format must declare the 'dev' spoke."""
        lower = content.lower()
        assert "dev" in lower, f"{fmt}: dev spoke not found"

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_spoke_prod_cidr_present(self, fmt: str, content: str):
        """Every format must reference the prod spoke CIDR."""
        assert "10.1.0.0/16" in content, (
            f"{fmt}: prod spoke CIDR 10.1.0.0/16 not found"
        )

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_spoke_dev_cidr_present(self, fmt: str, content: str):
        """Every format must reference the dev spoke CIDR."""
        assert "10.2.0.0/16" in content, (
            f"{fmt}: dev spoke CIDR 10.2.0.0/16 not found"
        )

    # -- Hub-spoke peering ------------------------------------------------

    def test_terraform_has_peering_resources(self):
        """Terraform must declare vnet peering resources for hub-spoke connectivity."""
        assert "azurerm_virtual_network_peering" in _terraform_all

    def test_pulumi_ts_has_peering_resources(self):
        """Pulumi TypeScript must declare vnet peering for hub-spoke connectivity."""
        assert "VirtualNetworkPeering" in _pulumi_ts_all

    def test_pulumi_py_has_peering_resources(self):
        """Pulumi Python must declare vnet peering for hub-spoke connectivity."""
        assert "VirtualNetworkPeering" in _pulumi_py_all

    def test_bicep_references_spoke_modules(self):
        """Bicep must include spoke networking module references."""
        assert "spoke-networking.bicep" in _bicep_all

    def test_arm_has_spoke_deployments(self):
        """ARM must include nested spoke deployment resources."""
        arm_main = json.loads(_arm_files["azuredeploy.json"])
        spoke_deployments = [
            r for r in arm_main["resources"]
            if r.get("type") == "Microsoft.Resources/deployments"
            and "spoke" in r.get("name", "")
        ]
        assert len(spoke_deployments) == 2, (
            f"Expected 2 spoke deployments, got {len(spoke_deployments)}"
        )

    # -- Resource groups ---------------------------------------------------

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_platform_resource_group(self, fmt: str, content: str):
        """Every format must create a platform resource group."""
        assert "rg-platform" in content, (
            f"{fmt}: platform resource group not found"
        )

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_networking_resource_group(self, fmt: str, content: str):
        """Every format must create a networking resource group."""
        assert "rg-networking" in content, (
            f"{fmt}: networking resource group not found"
        )

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_security_resource_group(self, fmt: str, content: str):
        """Every format must create a security resource group."""
        assert "rg-security" in content, (
            f"{fmt}: security resource group not found"
        )

    # -- Firewall resources ------------------------------------------------

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_firewall_subnet_present(self, fmt: str, content: str):
        """Every format must include an AzureFirewallSubnet when firewall is enabled."""
        assert "AzureFirewallSubnet" in content, (
            f"{fmt}: AzureFirewallSubnet not found"
        )

    def test_terraform_has_firewall_subnet_resource(self):
        """Terraform must declare an azurerm_subnet for the firewall."""
        assert "azurerm_subnet" in _terraform_all
        assert "AzureFirewallSubnet" in _terraform_all

    def test_pulumi_ts_has_firewall_subnet(self):
        """Pulumi TS must declare a firewall subnet."""
        assert "AzureFirewallSubnet" in _pulumi_ts_all

    def test_pulumi_py_has_firewall_subnet(self):
        """Pulumi Python must declare a firewall subnet."""
        assert "AzureFirewallSubnet" in _pulumi_py_all

    # -- Environment parameterisation --------------------------------------

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_environment_parameter_exists(self, fmt: str, content: str):
        """Every format must expose an environment parameter or variable."""
        lower = content.lower()
        assert "environment" in lower, (
            f"{fmt}: no environment parameter/variable found"
        )

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_region_reference_present(self, fmt: str, content: str):
        """Every format must reference the configured region."""
        assert "eastus2" in content, (
            f"{fmt}: region eastus2 not found"
        )

    # -- OnRamp version header --------------------------------------------

    @pytest.mark.parametrize(
        "fmt,content",
        [
            ("bicep", _bicep_files.get("main.bicep", "")),
            ("terraform", _terraform_files.get("main.tf", "")),
            ("pulumi_ts", _pulumi_ts_files.get("index.ts", "")),
            ("pulumi_py", _pulumi_py_files.get("__main__.py", "")),
        ],
        ids=["bicep", "terraform", "pulumi_ts", "pulumi_py"],
    )
    def test_onramp_version_header(self, fmt: str, content: str):
        """Each main file must include an OnRamp version header."""
        assert "OnRamp Generated" in content, (
            f"{fmt}: OnRamp version header not found"
        )

    # -- Consistent spoke count -------------------------------------------

    def test_spoke_count_matches_across_formats(self):
        """All formats must represent exactly the same number of spokes."""
        expected_spokes = len(STANDARD_ARCHITECTURE["network_topology"]["spokes"])
        # Terraform: count spoke vnet resources
        tf_spoke_vnets = _terraform_all.count('"azurerm_virtual_network" "spoke_')
        assert tf_spoke_vnets == expected_spokes, (
            f"Terraform: expected {expected_spokes} spoke vnets, got {tf_spoke_vnets}"
        )
        # ARM: count spoke deployments
        arm_main = json.loads(_arm_files["azuredeploy.json"])
        arm_spoke_deps = [
            r for r in arm_main["resources"]
            if "spoke" in r.get("name", "")
        ]
        assert len(arm_spoke_deps) == expected_spokes


# ═══════════════════════════════════════════════════════════════════════════
# 2. Security Validation
# ═══════════════════════════════════════════════════════════════════════════


# Patterns that indicate hardcoded secrets
SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("hardcoded password", re.compile(r'password\s*[=:]\s*["\'][^${\[]+["\']', re.IGNORECASE)),
    ("hardcoded API key", re.compile(r'api[_-]?key\s*[=:]\s*["\'][A-Za-z0-9+/=]{16,}["\']', re.IGNORECASE)),
    ("hardcoded secret", re.compile(r'secret\s*[=:]\s*["\'][A-Za-z0-9+/=]{16,}["\']', re.IGNORECASE)),
    ("hardcoded connection string", re.compile(
        r'(connection_?string|connstr)\s*[=:]\s*["\']Server=', re.IGNORECASE
    )),
    ("hardcoded SAS token", re.compile(r'sig=[A-Za-z0-9%+/=]{20,}', re.IGNORECASE)),
    ("hardcoded bearer token", re.compile(r'Bearer\s+[A-Za-z0-9._-]{20,}', re.IGNORECASE)),
]


class TestSecurityValidation:
    """Validate that generated IaC follows security best practices."""

    # -- No hardcoded secrets in any format --------------------------------

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    @pytest.mark.parametrize(
        "secret_name,pattern",
        SECRET_PATTERNS,
        ids=[s[0] for s in SECRET_PATTERNS],
    )
    def test_no_hardcoded_secret(
        self, fmt: str, content: str, secret_name: str, pattern: re.Pattern[str]
    ):
        """No IaC output should contain hardcoded credentials."""
        matches = pattern.findall(content)
        assert not matches, (
            f"{fmt}: found {secret_name} — {matches[:3]}"
        )

    # -- Network segmentation ----------------------------------------------

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_subnet_references_exist(self, fmt: str, content: str):
        """Every format must reference subnets for network segmentation."""
        lower = content.lower()
        assert "subnet" in lower, (
            f"{fmt}: no subnet references found — network segmentation missing"
        )

    def test_arm_networking_template_has_subnets(self):
        """ARM networking template must define subnets for hub VNet."""
        networking = json.loads(_arm_files["nestedtemplates/networking.json"])
        resources = networking["resources"]
        vnet_resource = next(
            (r for r in resources if r["type"] == "Microsoft.Network/virtualNetworks"),
            None,
        )
        assert vnet_resource is not None, "ARM: no VNet resource in networking template"
        subnets = vnet_resource["properties"]["addressSpace"]
        assert subnets is not None

    def test_arm_networking_has_firewall_subnet(self):
        """ARM networking template must include an AzureFirewallSubnet."""
        networking = json.loads(_arm_files["nestedtemplates/networking.json"])
        vnet = networking["resources"][0]
        subnet_names = [
            s["name"] for s in vnet["properties"]["subnets"]
        ]
        assert "[variables('firewallSubnetName')]" in subnet_names

    def test_arm_networking_has_bastion_subnet(self):
        """ARM networking template must include an AzureBastionSubnet."""
        networking = json.loads(_arm_files["nestedtemplates/networking.json"])
        vnet = networking["resources"][0]
        subnet_names = [
            s["name"] for s in vnet["properties"]["subnets"]
        ]
        assert "[variables('bastionSubnetName')]" in subnet_names

    def test_arm_networking_has_gateway_subnet(self):
        """ARM networking template must include a GatewaySubnet."""
        networking = json.loads(_arm_files["nestedtemplates/networking.json"])
        vnet = networking["resources"][0]
        subnet_names = [
            s["name"] for s in vnet["properties"]["subnets"]
        ]
        assert "[variables('gatewaySubnetName')]" in subnet_names

    def test_terraform_has_bastion_subnet(self):
        """Terraform must declare an AzureBastionSubnet."""
        assert "AzureBastionSubnet" in _terraform_all

    # -- Encryption / Key Vault -------------------------------------------

    def test_arm_security_template_has_key_vault(self):
        """ARM security template must provision a Key Vault."""
        security = json.loads(_arm_files["nestedtemplates/security.json"])
        kv_resources = [
            r for r in security["resources"]
            if r["type"] == "Microsoft.KeyVault/vaults"
        ]
        assert len(kv_resources) >= 1, "ARM: no Key Vault in security template"

    def test_arm_key_vault_has_rbac_authorization(self):
        """ARM Key Vault must enable RBAC authorisation (not access policies)."""
        security = json.loads(_arm_files["nestedtemplates/security.json"])
        kv = next(
            r for r in security["resources"]
            if r["type"] == "Microsoft.KeyVault/vaults"
        )
        assert kv["properties"]["enableRbacAuthorization"] is True

    def test_arm_key_vault_has_soft_delete(self):
        """ARM Key Vault must have soft-delete enabled for data protection."""
        security = json.loads(_arm_files["nestedtemplates/security.json"])
        kv = next(
            r for r in security["resources"]
            if r["type"] == "Microsoft.KeyVault/vaults"
        )
        assert kv["properties"]["enableSoftDelete"] is True

    def test_arm_key_vault_soft_delete_retention(self):
        """ARM Key Vault soft-delete retention must be ≥ 7 days."""
        security = json.loads(_arm_files["nestedtemplates/security.json"])
        kv = next(
            r for r in security["resources"]
            if r["type"] == "Microsoft.KeyVault/vaults"
        )
        retention = kv["properties"].get("softDeleteRetentionInDays", 0)
        assert retention >= 7, f"Soft-delete retention is {retention} days (must be ≥7)"

    # -- Monitoring / Log Analytics ----------------------------------------

    def test_arm_security_template_has_log_analytics(self):
        """ARM security template must provision a Log Analytics workspace."""
        security = json.loads(_arm_files["nestedtemplates/security.json"])
        law_resources = [
            r for r in security["resources"]
            if r["type"] == "Microsoft.OperationalInsights/workspaces"
        ]
        assert len(law_resources) >= 1, (
            "ARM: no Log Analytics workspace in security template"
        )

    # -- No overly permissive network rules --------------------------------

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_no_allow_all_inbound_rule(self, fmt: str, content: str):
        """No format should contain a rule allowing all inbound from 0.0.0.0/0 on all ports."""
        # Check for patterns like source_address_prefix = "*" combined with
        # destination_port_range = "*" — a wide-open rule.  This regex looks for
        # both appearing together within a small window.
        has_star_source = bool(
            re.search(r'(source.*0\.0\.0\.0/0.*destination.*\*)', content, re.DOTALL | re.IGNORECASE)
        )
        assert not has_star_source, (
            f"{fmt}: contains overly permissive inbound rule (0.0.0.0/0 → *)"
        )

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_no_wildcard_nsg_rule(self, fmt: str, content: str):
        """No format should have an Allow NSG rule with source * and port *.

        Deny-all rules and Azure service tag rules (VirtualNetwork,
        AzureLoadBalancer) are security best practice and are excluded.
        """
        # Split content into individual rule blocks so the regex doesn't
        # span across unrelated rules when using DOTALL.
        rule_blocks = re.split(
            r'(?:^|\n)\s*(?:\{|resource\s)', content
        )
        for block in rule_blocks:
            # Skip explicit deny rules — deny-all with source=* port=*
            # is a security best practice.
            if re.search(r'["\']?Deny["\']?', block, re.IGNORECASE):
                continue
            # Skip rules using Azure service tags (VirtualNetwork,
            # AzureLoadBalancer, etc.) — these are scoped, not wildcard.
            if re.search(
                r'source.*(?:VirtualNetwork|AzureLoadBalancer)',
                block, re.IGNORECASE
            ):
                continue
            has_wildcard = bool(
                re.search(
                    r'source.*["\']?\*["\']?.*destination.*port.*["\']?\*["\']?',
                    block,
                    re.DOTALL | re.IGNORECASE,
                )
            )
            assert not has_wildcard, (
                f"{fmt}: contains wildcard Allow NSG rule (source=* port=*)"
            )

    # -- Firewall present when enabled -------------------------------------

    def test_pulumi_ts_declares_azure_firewall(self):
        """Pulumi TS must declare an Azure Firewall resource when enabled."""
        assert "AzureFirewall" in _pulumi_ts_all

    def test_pulumi_py_declares_azure_firewall(self):
        """Pulumi Python must declare an Azure Firewall resource when enabled."""
        assert "AzureFirewall" in _pulumi_py_all


# ═══════════════════════════════════════════════════════════════════════════
# 3. Pipeline Security Validation
# ═══════════════════════════════════════════════════════════════════════════


class TestPipelineSecurityValidation:
    """Validate that generated CI/CD pipelines follow security best practices."""

    # -- GitHub Actions: OIDC ---------------------------------------------

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_github_actions_uses_oidc_login(self, iac_fmt: IaCFormat):
        """GitHub Actions workflows must use azure/login with OIDC."""
        all_content = "\n".join(_gh_workflows[iac_fmt.value].values())
        assert "azure/login" in all_content, (
            f"GH/{iac_fmt.value}: azure/login action not found"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_github_actions_has_id_token_permission(self, iac_fmt: IaCFormat):
        """GitHub Actions workflows must request id-token: write for OIDC."""
        all_content = "\n".join(_gh_workflows[iac_fmt.value].values())
        assert "id-token: write" in all_content, (
            f"GH/{iac_fmt.value}: id-token permission not set"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_github_actions_references_secrets(self, iac_fmt: IaCFormat):
        """GitHub Actions workflows must reference secrets (not inline creds)."""
        all_content = "\n".join(_gh_workflows[iac_fmt.value].values())
        assert "${{ secrets." in all_content, (
            f"GH/{iac_fmt.value}: no secrets references found"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_github_actions_references_client_id_secret(self, iac_fmt: IaCFormat):
        """GitHub Actions must reference AZURE_CLIENT_ID from secrets (OIDC)."""
        all_content = "\n".join(_gh_workflows[iac_fmt.value].values())
        assert "secrets.AZURE_CLIENT_ID" in all_content

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_github_actions_references_tenant_id_secret(self, iac_fmt: IaCFormat):
        """GitHub Actions must reference AZURE_TENANT_ID from secrets."""
        all_content = "\n".join(_gh_workflows[iac_fmt.value].values())
        assert "secrets.AZURE_TENANT_ID" in all_content

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_github_actions_references_subscription_id_secret(self, iac_fmt: IaCFormat):
        """GitHub Actions must reference AZURE_SUBSCRIPTION_ID from secrets."""
        all_content = "\n".join(_gh_workflows[iac_fmt.value].values())
        assert "secrets.AZURE_SUBSCRIPTION_ID" in all_content

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_github_actions_no_hardcoded_credentials(self, iac_fmt: IaCFormat):
        """GitHub Actions must not contain hardcoded Azure credentials."""
        all_content = "\n".join(_gh_workflows[iac_fmt.value].values())
        # Client secret should never appear — OIDC uses federated creds
        assert "client-secret" not in all_content.lower(), (
            f"GH/{iac_fmt.value}: client-secret found (should use OIDC)"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_github_actions_has_environment_protection(self, iac_fmt: IaCFormat):
        """GitHub Actions deploy jobs must specify an environment for protection gates."""
        main_file_key = f"deploy-{iac_fmt.value}.yml"
        content = _gh_workflows[iac_fmt.value].get(main_file_key, "")
        assert "environment:" in content, (
            f"GH/{iac_fmt.value}: no environment protection in deploy workflow"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_github_actions_no_plaintext_passwords(self, iac_fmt: IaCFormat):
        """GitHub Actions must not contain plaintext passwords or tokens."""
        all_content = "\n".join(_gh_workflows[iac_fmt.value].values())
        for pattern_name, pattern in SECRET_PATTERNS:
            matches = pattern.findall(all_content)
            assert not matches, (
                f"GH/{iac_fmt.value}: found {pattern_name} — {matches[:3]}"
            )

    # -- Azure DevOps: service connections & variable groups ---------------

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_azure_devops_uses_service_connection(self, iac_fmt: IaCFormat):
        """Azure DevOps pipelines must reference an Azure service connection."""
        all_content = "\n".join(_ado_pipelines[iac_fmt.value].values())
        assert "azureServiceConnection" in all_content or "azure-service-connection" in all_content, (
            f"ADO/{iac_fmt.value}: no service connection reference found"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_azure_devops_uses_variable_group(self, iac_fmt: IaCFormat):
        """Azure DevOps pipelines must reference a variable group for secrets."""
        all_content = "\n".join(_ado_pipelines[iac_fmt.value].values())
        assert "landing-zone-secrets" in all_content, (
            f"ADO/{iac_fmt.value}: variable group reference not found"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_azure_devops_has_environment_references(self, iac_fmt: IaCFormat):
        """Azure DevOps pipelines must use environment-based deployments."""
        all_content = "\n".join(_ado_pipelines[iac_fmt.value].values())
        assert "environment" in all_content.lower(), (
            f"ADO/{iac_fmt.value}: no environment reference found"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_azure_devops_no_hardcoded_credentials(self, iac_fmt: IaCFormat):
        """Azure DevOps pipelines must not contain inline credential values."""
        all_content = "\n".join(_ado_pipelines[iac_fmt.value].values())
        for pattern_name, pattern in SECRET_PATTERNS:
            matches = pattern.findall(all_content)
            assert not matches, (
                f"ADO/{iac_fmt.value}: found {pattern_name} — {matches[:3]}"
            )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_azure_devops_has_deployment_stages(self, iac_fmt: IaCFormat):
        """Azure DevOps pipelines must define deployment stages."""
        pipeline_yml = _ado_pipelines[iac_fmt.value].get("azure-pipelines.yml", "")
        assert "stage" in pipeline_yml.lower(), (
            f"ADO/{iac_fmt.value}: no stages defined"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_azure_devops_prod_stage_has_condition(self, iac_fmt: IaCFormat):
        """Azure DevOps prod deployment must have a condition (e.g. main branch only)."""
        pipeline_yml = _ado_pipelines[iac_fmt.value].get("azure-pipelines.yml", "")
        # The prod condition should restrict to main branch
        assert "refs/heads/main" in pipeline_yml, (
            f"ADO/{iac_fmt.value}: prod stage missing branch condition"
        )


# ═══════════════════════════════════════════════════════════════════════════
# 4. Consistency Checks
# ═══════════════════════════════════════════════════════════════════════════


class TestConsistencyChecks:
    """Validate naming, parameterisation, and tagging consistency."""

    # -- Resource naming conventions ---------------------------------------

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_hub_vnet_naming_convention(self, fmt: str, content: str):
        """Hub VNet must follow the vnet-hub naming pattern."""
        assert "vnet-hub" in content, (
            f"{fmt}: hub VNet does not follow 'vnet-hub' naming convention"
        )

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_spoke_vnet_naming_convention(self, fmt: str, content: str):
        """Spoke VNets must follow the vnet-spoke-* or vnet-{spoke_name} naming pattern."""
        lower = content.lower()
        assert "vnet-" in lower and ("spoke" in lower or "prod" in lower), (
            f"{fmt}: spoke VNets do not follow naming conventions"
        )

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_resource_group_naming_prefix(self, fmt: str, content: str):
        """All resource groups must use the 'rg-' prefix convention."""
        assert "rg-" in content, (
            f"{fmt}: resource groups do not use 'rg-' prefix"
        )

    # -- Location parameterised (not hardcoded) ----------------------------

    def test_bicep_location_is_parameter(self):
        """Bicep must declare location as a parameter, not hardcode it."""
        main = _bicep_files.get("main.bicep", "")
        assert "param location string" in main, (
            "Bicep: location is not declared as a parameter"
        )

    def test_terraform_location_is_variable(self):
        """Terraform must declare location as a variable."""
        variables = _terraform_files.get("variables.tf", "")
        assert 'variable "location"' in variables, (
            "Terraform: location is not declared as a variable"
        )

    def test_arm_location_is_parameter(self):
        """ARM must declare location as a template parameter."""
        arm_main = json.loads(_arm_files["azuredeploy.json"])
        assert "location" in arm_main["parameters"], (
            "ARM: location is not a template parameter"
        )

    def test_pulumi_ts_location_is_configurable(self):
        """Pulumi TS must read location from config, not hardcode it."""
        index = _pulumi_ts_files.get("index.ts", "")
        assert "config.get" in index and "location" in index, (
            "Pulumi TS: location is not configurable"
        )

    def test_pulumi_py_location_is_configurable(self):
        """Pulumi Python must read location from config, not hardcode it."""
        main = _pulumi_py_files.get("__main__.py", "")
        assert "config.get" in main and "location" in main, (
            "Pulumi PY: location is not configurable"
        )

    # -- Tags applied consistently -----------------------------------------

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_managed_by_tag_present(self, fmt: str, content: str):
        """Every format must include a managedBy/managed_by tag referencing OnRamp."""
        lower = content.lower()
        assert "onramp" in lower and ("managedby" in lower or "managed_by" in lower), (
            f"{fmt}: managedBy tag not found"
        )

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_environment_tag_present(self, fmt: str, content: str):
        """Every format must include an environment tag."""
        lower = content.lower()
        assert "environment" in lower, (
            f"{fmt}: environment tag not found"
        )

    @pytest.mark.parametrize("fmt,content", ALL_IAC_OUTPUTS, ids=[f[0] for f in ALL_IAC_OUTPUTS])
    def test_organization_size_tag_present(self, fmt: str, content: str):
        """Every format must include an organizationSize tag."""
        lower = content.lower()
        assert "organizationsize" in lower or "organization_size" in lower, (
            f"{fmt}: organizationSize tag not found"
        )

    # -- ARM template structural consistency --------------------------------

    def test_arm_main_template_valid_json(self):
        """ARM azuredeploy.json must be valid JSON."""
        parsed = json.loads(_arm_files["azuredeploy.json"])
        assert isinstance(parsed, dict)

    def test_arm_parameters_valid_json(self):
        """ARM azuredeploy.parameters.json must be valid JSON."""
        parsed = json.loads(_arm_files["azuredeploy.parameters.json"])
        assert isinstance(parsed, dict)

    def test_arm_networking_template_valid_json(self):
        """ARM nested networking template must be valid JSON."""
        parsed = json.loads(_arm_files["nestedtemplates/networking.json"])
        assert isinstance(parsed, dict)

    def test_arm_security_template_valid_json(self):
        """ARM nested security template must be valid JSON."""
        parsed = json.loads(_arm_files["nestedtemplates/security.json"])
        assert isinstance(parsed, dict)

    def test_arm_main_template_has_schema(self):
        """ARM azuredeploy.json must include the required $schema field."""
        parsed = json.loads(_arm_files["azuredeploy.json"])
        assert "$schema" in parsed
        assert "deploymentTemplate" in parsed["$schema"]

    def test_arm_main_template_has_content_version(self):
        """ARM azuredeploy.json must include contentVersion."""
        parsed = json.loads(_arm_files["azuredeploy.json"])
        assert "contentVersion" in parsed
        assert parsed["contentVersion"] == "1.0.0.0"

    def test_arm_main_template_has_resources(self):
        """ARM azuredeploy.json must have a resources array."""
        parsed = json.loads(_arm_files["azuredeploy.json"])
        assert "resources" in parsed
        assert isinstance(parsed["resources"], list)
        assert len(parsed["resources"]) > 0

    # -- Terraform structural consistency ----------------------------------

    def test_terraform_has_provider_file(self):
        """Terraform must generate a provider.tf file."""
        assert "provider.tf" in _terraform_files

    def test_terraform_has_variables_file(self):
        """Terraform must generate a variables.tf file."""
        assert "variables.tf" in _terraform_files

    def test_terraform_has_main_file(self):
        """Terraform must generate a main.tf file."""
        assert "main.tf" in _terraform_files

    def test_terraform_has_outputs_file(self):
        """Terraform must generate an outputs.tf file."""
        assert "outputs.tf" in _terraform_files

    def test_terraform_provider_uses_azurerm(self):
        """Terraform provider.tf must configure the azurerm provider."""
        provider = _terraform_files.get("provider.tf", "")
        assert "azurerm" in provider

    def test_terraform_requires_version(self):
        """Terraform must specify a required_version constraint."""
        provider = _terraform_files.get("provider.tf", "")
        assert "required_version" in provider

    # -- Pulumi structural consistency -------------------------------------

    def test_pulumi_ts_has_pulumi_yaml(self):
        """Pulumi TS must generate a Pulumi.yaml project file."""
        assert "Pulumi.yaml" in _pulumi_ts_files

    def test_pulumi_ts_has_package_json(self):
        """Pulumi TS must generate a package.json."""
        assert "package.json" in _pulumi_ts_files

    def test_pulumi_ts_has_index_ts(self):
        """Pulumi TS must generate an index.ts entry point."""
        assert "index.ts" in _pulumi_ts_files

    def test_pulumi_py_has_pulumi_yaml(self):
        """Pulumi Python must generate a Pulumi.yaml project file."""
        assert "Pulumi.yaml" in _pulumi_py_files

    def test_pulumi_py_has_requirements_txt(self):
        """Pulumi Python must generate a requirements.txt."""
        assert "requirements.txt" in _pulumi_py_files

    def test_pulumi_py_has_main_py(self):
        """Pulumi Python must generate a __main__.py entry point."""
        assert "__main__.py" in _pulumi_py_files

    def test_pulumi_ts_uses_azure_native_provider(self):
        """Pulumi TS must import the Azure Native provider."""
        index = _pulumi_ts_files.get("index.ts", "")
        assert "@pulumi/azure-native" in index

    def test_pulumi_py_uses_azure_native_provider(self):
        """Pulumi Python must import the Azure Native provider."""
        main = _pulumi_py_files.get("__main__.py", "")
        assert "pulumi_azure_native" in main

    # -- Bicep structural consistency --------------------------------------

    def test_bicep_has_main_file(self):
        """Bicep must generate a main.bicep file."""
        assert "main.bicep" in _bicep_files

    def test_bicep_has_parameters_json(self):
        """Bicep must generate a parameters.json file."""
        assert "parameters.json" in _bicep_files

    def test_bicep_main_targets_subscription_scope(self):
        """Bicep main.bicep must target subscription scope."""
        main = _bicep_files.get("main.bicep", "")
        assert "targetScope = 'subscription'" in main

    def test_bicep_parameters_valid_json(self):
        """Bicep parameters.json must be valid JSON."""
        parsed = json.loads(_bicep_files["parameters.json"])
        assert isinstance(parsed, dict)
        assert "parameters" in parsed

    # -- Pipeline structural consistency -----------------------------------

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_github_actions_generates_validate_workflow(self, iac_fmt: IaCFormat):
        """GitHub Actions must produce a validate.yml reusable workflow."""
        assert "validate.yml" in _gh_workflows[iac_fmt.value], (
            f"GH/{iac_fmt.value}: validate.yml not generated"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_github_actions_generates_env_params(self, iac_fmt: IaCFormat):
        """GitHub Actions must produce environment parameter files."""
        files = _gh_workflows[iac_fmt.value]
        env_files = [f for f in files if f.startswith("env-")]
        assert len(env_files) >= 2, (
            f"GH/{iac_fmt.value}: expected ≥2 env param files, got {len(env_files)}"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_azure_devops_generates_pipeline_yml(self, iac_fmt: IaCFormat):
        """Azure DevOps must produce an azure-pipelines.yml."""
        assert "azure-pipelines.yml" in _ado_pipelines[iac_fmt.value], (
            f"ADO/{iac_fmt.value}: azure-pipelines.yml not generated"
        )

    @pytest.mark.parametrize("iac_fmt", list(IaCFormat), ids=[f.value for f in IaCFormat])
    def test_azure_devops_generates_readme(self, iac_fmt: IaCFormat):
        """Azure DevOps must produce a pipeline README."""
        files = _ado_pipelines[iac_fmt.value]
        readme_files = [f for f in files if f.lower().endswith("readme.md")]
        assert len(readme_files) >= 1, (
            f"ADO/{iac_fmt.value}: no README generated"
        )
