"""Azure Confidential Computing service.

Provides data and recommendation logic for confidential computing options
including Confidential VMs (SEV-SNP), SGX Enclaves, Confidential Containers,
Azure Confidential Ledger, Always Encrypted with secure enclaves, and
Azure Attestation.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# ── Confidential VM SKU Data ─────────────────────────────────────────────────

CONFIDENTIAL_VM_SKUS: list[dict] = [
    # AMD SEV-SNP series
    {
        "name": "Standard_DC2as_v5",
        "series": "DCasv5",
        "vcpus": 2,
        "memory_gb": 8,
        "tee_type": "SEV-SNP",
        "vendor": "AMD",
        "max_data_disks": 4,
        "description": "Confidential VM with AMD SEV-SNP, 2 vCPUs, 8 GiB RAM.",
    },
    {
        "name": "Standard_DC4as_v5",
        "series": "DCasv5",
        "vcpus": 4,
        "memory_gb": 16,
        "tee_type": "SEV-SNP",
        "vendor": "AMD",
        "max_data_disks": 8,
        "description": "Confidential VM with AMD SEV-SNP, 4 vCPUs, 16 GiB RAM.",
    },
    {
        "name": "Standard_DC8as_v5",
        "series": "DCasv5",
        "vcpus": 8,
        "memory_gb": 32,
        "tee_type": "SEV-SNP",
        "vendor": "AMD",
        "max_data_disks": 16,
        "description": "Confidential VM with AMD SEV-SNP, 8 vCPUs, 32 GiB RAM.",
    },
    {
        "name": "Standard_DC16as_v5",
        "series": "DCasv5",
        "vcpus": 16,
        "memory_gb": 64,
        "tee_type": "SEV-SNP",
        "vendor": "AMD",
        "max_data_disks": 32,
        "description": "Confidential VM with AMD SEV-SNP, 16 vCPUs, 64 GiB RAM.",
    },
    {
        "name": "Standard_DC2ads_v5",
        "series": "DCadsv5",
        "vcpus": 2,
        "memory_gb": 8,
        "tee_type": "SEV-SNP",
        "vendor": "AMD",
        "max_data_disks": 4,
        "description": "Confidential VM with local temp disk, AMD SEV-SNP, 2 vCPUs.",
    },
    {
        "name": "Standard_DC4ads_v5",
        "series": "DCadsv5",
        "vcpus": 4,
        "memory_gb": 16,
        "tee_type": "SEV-SNP",
        "vendor": "AMD",
        "max_data_disks": 8,
        "description": "Confidential VM with local temp disk, AMD SEV-SNP, 4 vCPUs.",
    },
    {
        "name": "Standard_EC2as_v5",
        "series": "ECasv5",
        "vcpus": 2,
        "memory_gb": 16,
        "tee_type": "SEV-SNP",
        "vendor": "AMD",
        "max_data_disks": 4,
        "description": "Memory-optimized confidential VM, AMD SEV-SNP, 2 vCPUs.",
    },
    {
        "name": "Standard_EC4as_v5",
        "series": "ECasv5",
        "vcpus": 4,
        "memory_gb": 32,
        "tee_type": "SEV-SNP",
        "vendor": "AMD",
        "max_data_disks": 8,
        "description": "Memory-optimized confidential VM, AMD SEV-SNP, 4 vCPUs.",
    },
    {
        "name": "Standard_EC2ads_v5",
        "series": "ECadsv5",
        "vcpus": 2,
        "memory_gb": 16,
        "tee_type": "SEV-SNP",
        "vendor": "AMD",
        "max_data_disks": 4,
        "description": "Memory-optimized CC VM with temp disk, AMD SEV-SNP, 2 vCPUs.",
    },
    # Intel SGX series
    {
        "name": "Standard_DC2s_v3",
        "series": "DCsv3",
        "vcpus": 2,
        "memory_gb": 16,
        "tee_type": "SGX",
        "vendor": "Intel",
        "enclave_memory_mb": 8192,
        "max_data_disks": 4,
        "description": "SGX enclave-capable VM, 2 vCPUs, 8 GiB enclave memory.",
    },
    {
        "name": "Standard_DC4s_v3",
        "series": "DCsv3",
        "vcpus": 4,
        "memory_gb": 32,
        "tee_type": "SGX",
        "vendor": "Intel",
        "enclave_memory_mb": 16384,
        "max_data_disks": 8,
        "description": "SGX enclave-capable VM, 4 vCPUs, 16 GiB enclave memory.",
    },
    {
        "name": "Standard_DC8s_v3",
        "series": "DCsv3",
        "vcpus": 8,
        "memory_gb": 64,
        "tee_type": "SGX",
        "vendor": "Intel",
        "enclave_memory_mb": 32768,
        "max_data_disks": 16,
        "description": "SGX enclave-capable VM, 8 vCPUs, 32 GiB enclave memory.",
    },
    {
        "name": "Standard_DC2ds_v3",
        "series": "DCdsv3",
        "vcpus": 2,
        "memory_gb": 16,
        "tee_type": "SGX",
        "vendor": "Intel",
        "enclave_memory_mb": 8192,
        "max_data_disks": 4,
        "description": "SGX enclave VM with local temp disk, 2 vCPUs.",
    },
    {
        "name": "Standard_DC4ds_v3",
        "series": "DCdsv3",
        "vcpus": 4,
        "memory_gb": 32,
        "tee_type": "SGX",
        "vendor": "Intel",
        "enclave_memory_mb": 16384,
        "max_data_disks": 8,
        "description": "SGX enclave VM with local temp disk, 4 vCPUs.",
    },
]

# ── Confidential Computing Options ───────────────────────────────────────────

CONFIDENTIAL_OPTIONS: list[dict] = [
    {
        "id": "confidential_vms",
        "name": "Confidential VMs",
        "category": "compute",
        "tee_types": ["SEV-SNP"],
        "description": (
            "Azure Confidential VMs use AMD SEV-SNP to encrypt the entire VM"
            " including OS disk, memory, and vTPM state. Data remains encrypted"
            " in use, protecting against host-level attacks."
        ),
        "use_cases": [
            "Lift-and-shift migration of sensitive workloads",
            "Multi-tenant data isolation",
            "Regulated industries (healthcare, finance, government)",
        ],
        "vm_series": ["DCasv5", "DCadsv5", "ECasv5", "ECadsv5"],
        "attestation_supported": True,
    },
    {
        "id": "sgx_enclaves",
        "name": "SGX Enclaves",
        "category": "compute",
        "tee_types": ["SGX"],
        "description": (
            "Intel SGX enclaves provide application-level isolation with"
            " hardware-enforced memory encryption. Ideal for processing"
            " sensitive data in small, verifiable code regions."
        ),
        "use_cases": [
            "Secure multi-party computation",
            "Key management and cryptographic operations",
            "Confidential machine learning inference",
        ],
        "vm_series": ["DCsv3", "DCdsv3"],
        "attestation_supported": True,
    },
    {
        "id": "confidential_containers",
        "name": "Confidential Containers on AKS",
        "category": "containers",
        "tee_types": ["SEV-SNP", "SGX"],
        "description": (
            "Run container workloads in hardware-backed TEEs on AKS."
            " Supports both AMD SEV-SNP (pod-level) and Intel SGX"
            " (application-level) for container isolation."
        ),
        "use_cases": [
            "Confidential microservices",
            "Secure data pipelines in Kubernetes",
            "Multi-party analytics with container isolation",
        ],
        "vm_series": ["DCasv5", "DCsv3"],
        "attestation_supported": True,
    },
    {
        "id": "confidential_ledger",
        "name": "Azure Confidential Ledger",
        "category": "data",
        "tee_types": ["SGX"],
        "description": (
            "Tamper-proof, append-only data store backed by SGX enclaves."
            " Provides cryptographic verification of data integrity and"
            " is ideal for audit trails and immutable record-keeping."
        ),
        "use_cases": [
            "Immutable audit logs",
            "Financial transaction records",
            "Supply chain provenance tracking",
        ],
        "vm_series": [],
        "attestation_supported": True,
    },
    {
        "id": "always_encrypted",
        "name": "Always Encrypted with Secure Enclaves",
        "category": "data",
        "tee_types": ["SGX"],
        "description": (
            "SQL Server Always Encrypted uses SGX enclaves to perform"
            " rich computations on encrypted data without exposing"
            " plaintext to the database engine or administrators."
        ),
        "use_cases": [
            "Encrypted database queries on sensitive columns",
            "Pattern matching and range queries on encrypted data",
            "Regulatory compliance for data-at-rest and data-in-use",
        ],
        "vm_series": [],
        "attestation_supported": True,
    },
    {
        "id": "azure_attestation",
        "name": "Azure Attestation",
        "category": "security",
        "tee_types": ["SEV-SNP", "SGX"],
        "description": (
            "Remote attestation service that verifies the integrity of"
            " TEE environments. Validates platform state, enclave identity,"
            " and firmware configuration before granting access to secrets."
        ),
        "use_cases": [
            "Verify TEE integrity before releasing secrets",
            "Zero-trust key release workflows",
            "Compliance evidence for confidential workloads",
        ],
        "vm_series": [],
        "attestation_supported": False,
    },
]

# ── Supported Regions ────────────────────────────────────────────────────────

SUPPORTED_REGIONS: list[dict] = [
    {
        "name": "eastus",
        "display_name": "East US",
        "tee_types": ["SEV-SNP", "SGX"],
        "services": [
            "confidential_vms",
            "sgx_enclaves",
            "confidential_containers",
            "confidential_ledger",
            "always_encrypted",
            "azure_attestation",
        ],
    },
    {
        "name": "eastus2",
        "display_name": "East US 2",
        "tee_types": ["SEV-SNP", "SGX"],
        "services": [
            "confidential_vms",
            "sgx_enclaves",
            "confidential_containers",
            "azure_attestation",
        ],
    },
    {
        "name": "westus",
        "display_name": "West US",
        "tee_types": ["SEV-SNP"],
        "services": ["confidential_vms", "azure_attestation"],
    },
    {
        "name": "westeurope",
        "display_name": "West Europe",
        "tee_types": ["SEV-SNP", "SGX"],
        "services": [
            "confidential_vms",
            "sgx_enclaves",
            "confidential_containers",
            "confidential_ledger",
            "always_encrypted",
            "azure_attestation",
        ],
    },
    {
        "name": "northeurope",
        "display_name": "North Europe",
        "tee_types": ["SEV-SNP", "SGX"],
        "services": [
            "confidential_vms",
            "sgx_enclaves",
            "confidential_containers",
            "azure_attestation",
        ],
    },
    {
        "name": "uksouth",
        "display_name": "UK South",
        "tee_types": ["SEV-SNP", "SGX"],
        "services": [
            "confidential_vms",
            "sgx_enclaves",
            "confidential_containers",
            "azure_attestation",
        ],
    },
    {
        "name": "canadacentral",
        "display_name": "Canada Central",
        "tee_types": ["SEV-SNP"],
        "services": ["confidential_vms", "azure_attestation"],
    },
    {
        "name": "southeastasia",
        "display_name": "Southeast Asia",
        "tee_types": ["SEV-SNP"],
        "services": [
            "confidential_vms",
            "confidential_containers",
            "azure_attestation",
        ],
    },
]

# ── Attestation Configurations ───────────────────────────────────────────────

ATTESTATION_CONFIGS: dict[str, dict] = {
    "confidential_vms": {
        "cc_type": "confidential_vms",
        "attestation_provider": "Azure Attestation",
        "protocol": "Microsoft Azure Attestation (MAA)",
        "evidence_type": "SEV-SNP report",
        "key_release_policy": "maa_key_release",
        "steps": [
            "Deploy Azure Attestation provider in the target region.",
            "Configure VM to use vTPM-based attestation.",
            "Set key release policy on Key Vault or mHSM.",
            "VM requests attestation token from MAA on boot.",
            "MAA validates SEV-SNP report and returns signed token.",
            "Token presented to Key Vault to release encryption keys.",
        ],
    },
    "sgx_enclaves": {
        "cc_type": "sgx_enclaves",
        "attestation_provider": "Azure Attestation",
        "protocol": "Intel DCAP / Microsoft Azure Attestation",
        "evidence_type": "SGX quote",
        "key_release_policy": "sgx_enclave_policy",
        "steps": [
            "Deploy Azure Attestation provider with SGX policy.",
            "Enclave generates SGX quote with MRENCLAVE/MRSIGNER.",
            "Quote sent to MAA for verification.",
            "MAA validates quote against configured policy.",
            "Signed attestation token returned to client.",
            "Token used to access secrets from Key Vault or custom service.",
        ],
    },
    "confidential_containers": {
        "cc_type": "confidential_containers",
        "attestation_provider": "Azure Attestation",
        "protocol": "Container-level attestation via Kata/SEV-SNP",
        "evidence_type": "SEV-SNP report with container policy",
        "key_release_policy": "container_attestation_policy",
        "steps": [
            "Enable confidential node pool in AKS cluster.",
            "Deploy Azure Attestation provider.",
            "Configure container attestation policy (rego/json).",
            "Pod runtime generates SEV-SNP attestation report.",
            "Sidecar proxy forwards report to MAA for validation.",
            "Validated token enables encrypted data access.",
        ],
    },
    "confidential_ledger": {
        "cc_type": "confidential_ledger",
        "attestation_provider": "Built-in (Ledger-managed)",
        "protocol": "TLS-based enclave attestation",
        "evidence_type": "Enclave quote embedded in TLS handshake",
        "key_release_policy": "ledger_internal",
        "steps": [
            "Create Azure Confidential Ledger instance.",
            "Client SDK verifies enclave quote during TLS connection.",
            "Ledger nodes run inside SGX enclaves.",
            "All writes are signed and appended to tamper-proof log.",
            "Receipts provide cryptographic proof of inclusion.",
        ],
    },
    "always_encrypted": {
        "cc_type": "always_encrypted",
        "attestation_provider": "Azure Attestation or Host Guardian Service",
        "protocol": "Enclave attestation via SQL client driver",
        "evidence_type": "SGX enclave quote",
        "key_release_policy": "always_encrypted_enclave_policy",
        "steps": [
            "Enable Always Encrypted with secure enclaves on SQL DB.",
            "Deploy Azure Attestation provider for enclave validation.",
            "Configure column master key with enclave computations.",
            "Client driver attests enclave before sending column keys.",
            "Enclave decrypts and processes queries on encrypted data.",
            "Results re-encrypted before leaving enclave boundary.",
        ],
    },
    "azure_attestation": {
        "cc_type": "azure_attestation",
        "attestation_provider": "Self (Azure Attestation is the provider)",
        "protocol": "REST API with JSON Web Tokens",
        "evidence_type": "Platform-specific (SGX quote or SEV-SNP report)",
        "key_release_policy": "custom_policy",
        "steps": [
            "Create Azure Attestation provider instance.",
            "Upload custom attestation policies (if needed).",
            "TEE workload generates platform evidence.",
            "Evidence submitted to attestation endpoint.",
            "Provider evaluates evidence against policy.",
            "Returns signed JWT attestation token on success.",
        ],
    },
}


class ConfidentialComputingService:
    """Service for Azure confidential computing capabilities.

    Provides information about confidential computing options, VM SKUs,
    supported regions, and generates recommendations and architecture
    overlays for confidential workloads.
    """

    def get_confidential_options(self) -> list[dict]:
        """Return all confidential computing options with details."""
        return CONFIDENTIAL_OPTIONS

    def get_vm_skus(self) -> list[dict]:
        """Return all confidential computing-capable VM SKUs."""
        return CONFIDENTIAL_VM_SKUS

    def get_supported_regions(self) -> list[dict]:
        """Return regions with confidential computing support."""
        return SUPPORTED_REGIONS

    def recommend_confidential_config(
        self, workload_type: str, requirements: dict
    ) -> dict:
        """Recommend a confidential computing configuration.

        Args:
            workload_type: Type of workload (e.g. "web_app", "database",
                "container", "ledger", "multi_party").
            requirements: Dict with optional keys: min_vcpus, min_memory_gb,
                tee_preference, needs_attestation, region.

        Returns:
            Recommendation dict with cc_option, recommended_skus,
            region_options, attestation, and rationale.
        """
        tee_pref = requirements.get("tee_preference", "")
        min_vcpus = requirements.get("min_vcpus", 2)
        min_memory = requirements.get("min_memory_gb", 8)
        region = requirements.get("region", "")
        needs_attestation = requirements.get("needs_attestation", True)

        # Determine best CC option based on workload type
        option_map: dict[str, str] = {
            "web_app": "confidential_vms",
            "database": "always_encrypted",
            "container": "confidential_containers",
            "ledger": "confidential_ledger",
            "multi_party": "sgx_enclaves",
            "key_management": "sgx_enclaves",
            "microservices": "confidential_containers",
            "audit_trail": "confidential_ledger",
        }
        recommended_option_id = option_map.get(workload_type, "confidential_vms")

        # Override based on TEE preference
        if tee_pref == "SGX":
            if workload_type in ("web_app", "container"):
                recommended_option_id = "sgx_enclaves"
        elif tee_pref == "SEV-SNP":
            if workload_type in ("multi_party", "key_management"):
                recommended_option_id = "confidential_vms"

        # Find the CC option details
        cc_option = next(
            (o for o in CONFIDENTIAL_OPTIONS if o["id"] == recommended_option_id),
            CONFIDENTIAL_OPTIONS[0],
        )

        # Filter VM SKUs if applicable
        recommended_skus = []
        if cc_option["vm_series"]:
            target_tee = tee_pref if tee_pref else cc_option["tee_types"][0]
            recommended_skus = [
                sku
                for sku in CONFIDENTIAL_VM_SKUS
                if sku["tee_type"] == target_tee
                and sku["vcpus"] >= min_vcpus
                and sku["memory_gb"] >= min_memory
            ]
            # Fall back to any matching TEE type if too restrictive
            if not recommended_skus:
                recommended_skus = [
                    sku
                    for sku in CONFIDENTIAL_VM_SKUS
                    if sku["tee_type"] == target_tee
                ]

        # Filter regions
        region_options = SUPPORTED_REGIONS
        if region:
            region_options = [
                r for r in SUPPORTED_REGIONS if r["name"] == region
            ]
        region_options = [
            r
            for r in region_options
            if recommended_option_id in r["services"]
        ]

        # Build attestation config
        attestation = None
        if needs_attestation and recommended_option_id in ATTESTATION_CONFIGS:
            attestation = ATTESTATION_CONFIGS[recommended_option_id]

        rationale = (
            f"For '{workload_type}' workloads, '{cc_option['name']}' provides"
            f" the best combination of security isolation and operational"
            f" simplicity."
        )
        if tee_pref:
            rationale += f" Configured for {tee_pref} as requested."

        return {
            "workload_type": workload_type,
            "recommended_option": cc_option,
            "recommended_skus": recommended_skus[:5],
            "region_options": region_options,
            "attestation": attestation,
            "rationale": rationale,
        }

    def generate_confidential_architecture(
        self, base_architecture: dict, cc_options: dict
    ) -> dict:
        """Overlay confidential computing onto an existing architecture.

        Args:
            base_architecture: The base landing zone architecture dict.
            cc_options: Dict with keys: cc_type (str), vm_sku (optional str),
                region (optional str), enable_attestation (bool).

        Returns:
            Enhanced architecture dict with confidential computing layer.
        """
        cc_type = cc_options.get("cc_type", "confidential_vms")
        vm_sku = cc_options.get("vm_sku", "Standard_DC4as_v5")
        region = cc_options.get("region", "eastus")
        enable_attestation = cc_options.get("enable_attestation", True)

        # Find the CC option details
        cc_option = next(
            (o for o in CONFIDENTIAL_OPTIONS if o["id"] == cc_type),
            CONFIDENTIAL_OPTIONS[0],
        )

        # Build the confidential computing layer
        cc_layer: dict = {
            "confidential_computing": {
                "enabled": True,
                "type": cc_type,
                "option_details": {
                    "name": cc_option["name"],
                    "category": cc_option["category"],
                    "tee_types": cc_option["tee_types"],
                },
                "region": region,
            }
        }

        # Add VM configuration if applicable
        if cc_option["vm_series"]:
            sku_details = next(
                (s for s in CONFIDENTIAL_VM_SKUS if s["name"] == vm_sku),
                None,
            )
            cc_layer["confidential_computing"]["vm_configuration"] = {
                "sku": vm_sku,
                "details": sku_details,
            }

        # Add attestation configuration
        if enable_attestation and cc_type in ATTESTATION_CONFIGS:
            cc_layer["confidential_computing"]["attestation"] = {
                "enabled": True,
                "provider": "Azure Attestation",
                "config": ATTESTATION_CONFIGS[cc_type],
            }

        # Add security recommendations
        cc_layer["confidential_computing"]["security_recommendations"] = [
            "Use Azure Key Vault with mHSM for key management.",
            "Enable disk encryption with platform-managed or customer-managed keys.",
            "Configure network security groups to restrict TEE management traffic.",
            "Enable Microsoft Defender for Cloud for confidential VM monitoring.",
            "Implement zero-trust key release policies tied to attestation.",
        ]

        # Merge with base architecture
        enhanced = {**base_architecture, **cc_layer}
        return enhanced

    def get_attestation_config(self, cc_type: str) -> dict:
        """Get attestation configuration for a given CC type.

        Args:
            cc_type: Confidential computing type ID (e.g. "confidential_vms").

        Returns:
            Attestation configuration dict, or empty dict if not found.
        """
        return ATTESTATION_CONFIGS.get(cc_type, {})


confidential_computing_service = ConfidentialComputingService()
