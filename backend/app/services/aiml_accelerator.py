"""AI/ML landing zone accelerator for specialized workload architectures.

Provides GPU SKU recommendations, MLOps-aware architecture generation,
reference architectures and best-practice guidance for machine learning
workloads on Azure.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GPU_SKU_CATALOG: list[dict[str, Any]] = [
    {
        "id": "nc24ads_a100_v4",
        "name": "Standard_NC24ads_A100_v4",
        "family": "NC",
        "gpu_type": "A100",
        "gpu_count": 1,
        "gpu_memory_gb": 80,
        "vcpus": 24,
        "ram_gb": 220,
        "use_case": "Large-scale training, fine-tuning LLMs",
        "price_tier": "premium",
    },
    {
        "id": "nc48ads_a100_v4",
        "name": "Standard_NC48ads_A100_v4",
        "family": "NC",
        "gpu_type": "A100",
        "gpu_count": 2,
        "gpu_memory_gb": 160,
        "vcpus": 48,
        "ram_gb": 440,
        "use_case": "Multi-GPU training, distributed workloads",
        "price_tier": "premium",
    },
    {
        "id": "nd96asr_v4",
        "name": "Standard_ND96asr_v4",
        "family": "ND",
        "gpu_type": "A100",
        "gpu_count": 8,
        "gpu_memory_gb": 640,
        "vcpus": 96,
        "ram_gb": 900,
        "use_case": "Multi-node distributed training",
        "price_tier": "premium",
    },
    {
        "id": "nd96amsr_a100_v4",
        "name": "Standard_ND96amsr_A100_v4",
        "family": "ND",
        "gpu_type": "A100",
        "gpu_count": 8,
        "gpu_memory_gb": 640,
        "vcpus": 96,
        "ram_gb": 1900,
        "use_case": "HPC-grade distributed training",
        "price_tier": "premium",
    },
    {
        "id": "nd96isr_h100_v5",
        "name": "Standard_ND96isr_H100_v5",
        "family": "ND",
        "gpu_type": "H100",
        "gpu_count": 8,
        "gpu_memory_gb": 640,
        "vcpus": 96,
        "ram_gb": 1900,
        "use_case": "Cutting-edge LLM training, generative AI",
        "price_tier": "ultra",
    },
    {
        "id": "nc4as_t4_v3",
        "name": "Standard_NC4as_T4_v3",
        "family": "NC",
        "gpu_type": "T4",
        "gpu_count": 1,
        "gpu_memory_gb": 16,
        "vcpus": 4,
        "ram_gb": 28,
        "use_case": "Cost-effective inference, dev/test",
        "price_tier": "standard",
    },
    {
        "id": "nc64as_t4_v3",
        "name": "Standard_NC64as_T4_v3",
        "family": "NC",
        "gpu_type": "T4",
        "gpu_count": 4,
        "gpu_memory_gb": 64,
        "vcpus": 64,
        "ram_gb": 440,
        "use_case": "Multi-GPU inference at scale",
        "price_tier": "standard",
    },
    {
        "id": "nc6s_v3",
        "name": "Standard_NC6s_v3",
        "family": "NC",
        "gpu_type": "V100",
        "gpu_count": 1,
        "gpu_memory_gb": 16,
        "vcpus": 6,
        "ram_gb": 112,
        "use_case": "Medium-scale training, inference",
        "price_tier": "standard",
    },
    {
        "id": "nc24s_v3",
        "name": "Standard_NC24s_v3",
        "family": "NC",
        "gpu_type": "V100",
        "gpu_count": 4,
        "gpu_memory_gb": 64,
        "vcpus": 24,
        "ram_gb": 448,
        "use_case": "Multi-GPU training workloads",
        "price_tier": "standard",
    },
    {
        "id": "nv36ads_a10_v5",
        "name": "Standard_NV36ads_A10_v5",
        "family": "NV",
        "gpu_type": "A10",
        "gpu_count": 1,
        "gpu_memory_gb": 24,
        "vcpus": 36,
        "ram_gb": 440,
        "use_case": "Visualization, rendering, light inference",
        "price_tier": "standard",
    },
]

_QUESTIONS: list[dict[str, Any]] = [
    {
        "id": "ml_workload_type",
        "text": "What type of ML workload will you run?",
        "type": "select",
        "options": [
            {"value": "training", "label": "Training only"},
            {"value": "inference", "label": "Inference only"},
            {"value": "both", "label": "Training and inference"},
        ],
        "required": True,
        "category": "ai_ml",
        "help_text": "Choose your primary workload type.",
    },
    {
        "id": "gpu_requirements",
        "text": "What are your GPU requirements?",
        "type": "select",
        "options": [
            {"value": "none", "label": "No GPU needed"},
            {"value": "single", "label": "Single GPU"},
            {"value": "multi_gpu", "label": "Multi-GPU (single node)"},
            {"value": "multi_node", "label": "Multi-node GPU cluster"},
        ],
        "required": True,
        "category": "ai_ml",
        "help_text": "Select based on model size and training needs.",
    },
    {
        "id": "ml_framework",
        "text": "Which ML framework will you use?",
        "type": "select",
        "options": [
            {"value": "pytorch", "label": "PyTorch"},
            {"value": "tensorflow", "label": "TensorFlow"},
            {"value": "onnx", "label": "ONNX Runtime"},
            {"value": "huggingface", "label": "Hugging Face Transformers"},
            {"value": "custom", "label": "Custom / Other"},
        ],
        "required": True,
        "category": "ai_ml",
        "help_text": "Framework choice affects compute optimization.",
    },
    {
        "id": "data_volume",
        "text": "What is your expected data volume?",
        "type": "select",
        "options": [
            {"value": "small", "label": "< 100 GB"},
            {"value": "medium", "label": "100 GB – 1 TB"},
            {"value": "large", "label": "1 TB – 10 TB"},
            {"value": "very_large", "label": "> 10 TB (petabyte scale)"},
        ],
        "required": True,
        "category": "ai_ml",
        "help_text": "Data volume determines storage and networking.",
    },
    {
        "id": "realtime_inference",
        "text": "Do you need real-time inference endpoints?",
        "type": "boolean",
        "required": True,
        "category": "ai_ml",
        "help_text": "Real-time inference needs managed online endpoints.",
    },
    {
        "id": "mlops_maturity",
        "text": "What is your MLOps maturity level?",
        "type": "select",
        "options": [
            {"value": "ad_hoc", "label": "Ad-hoc (manual experiments)"},
            {"value": "basic_cicd", "label": "Basic CI/CD for models"},
            {"value": "full_mlops", "label": "Full MLOps pipeline"},
        ],
        "required": True,
        "category": "ai_ml",
        "help_text": "Maturity level shapes automation resources.",
    },
    {
        "id": "experiment_tracking",
        "text": "Do you need experiment tracking?",
        "type": "boolean",
        "required": True,
        "category": "ai_ml",
        "help_text": "Track metrics, params & artifacts across runs.",
    },
    {
        "id": "model_registry",
        "text": "Do you need a model registry?",
        "type": "boolean",
        "required": True,
        "category": "ai_ml",
        "help_text": "Central catalog for versioned model artifacts.",
    },
    {
        "id": "data_labeling",
        "text": "Do you need data labeling capabilities?",
        "type": "boolean",
        "required": True,
        "category": "ai_ml",
        "help_text": "Azure ML data labeling for annotation workflows.",
    },
    {
        "id": "responsible_ai",
        "text": "What responsible AI requirements apply?",
        "type": "multiselect",
        "options": [
            {"value": "fairness", "label": "Fairness assessment"},
            {"value": "explainability", "label": "Model explainability"},
            {"value": "privacy", "label": "Differential privacy"},
            {"value": "safety", "label": "Content safety filters"},
            {"value": "none", "label": "None at this time"},
        ],
        "required": True,
        "category": "ai_ml",
        "help_text": "Select all responsible AI capabilities needed.",
    },
    {
        "id": "optional_services",
        "text": "Which optional AI services do you need?",
        "type": "multiselect",
        "options": [
            {"value": "cognitive_services", "label": "Azure Cognitive Services"},
            {"value": "openai", "label": "Azure OpenAI Service"},
            {"value": "databricks", "label": "Azure Databricks"},
            {"value": "none", "label": "None"},
        ],
        "required": False,
        "category": "ai_ml",
        "help_text": "Additional AI/ML platform services.",
    },
    {
        "id": "team_size",
        "text": "How many data scientists / ML engineers?",
        "type": "select",
        "options": [
            {"value": "small", "label": "1 – 5"},
            {"value": "medium", "label": "6 – 20"},
            {"value": "large", "label": "21 – 50"},
            {"value": "enterprise", "label": "50+"},
        ],
        "required": False,
        "category": "ai_ml",
        "help_text": "Team size impacts compute instance count.",
    },
]

_BEST_PRACTICES: list[dict[str, Any]] = [
    {
        "id": "bp_data_governance",
        "title": "Implement data governance",
        "category": "data",
        "priority": "high",
        "description": (
            "Use Azure Purview / Microsoft Purview for data cataloging, "
            "lineage tracking and access policies across your ML data estate."
        ),
    },
    {
        "id": "bp_model_versioning",
        "title": "Version all model artifacts",
        "category": "mlops",
        "priority": "high",
        "description": (
            "Register every trained model in the Azure ML model registry "
            "with semantic versioning, lineage metadata and evaluation "
            "metrics attached."
        ),
    },
    {
        "id": "bp_responsible_ai",
        "title": "Integrate Responsible AI dashboard",
        "category": "governance",
        "priority": "high",
        "description": (
            "Enable the Responsible AI dashboard in Azure ML for fairness, "
            "explainability, error analysis and causal reasoning on every "
            "production model."
        ),
    },
    {
        "id": "bp_cost_optimization",
        "title": "Optimize GPU compute costs",
        "category": "cost",
        "priority": "medium",
        "description": (
            "Use low-priority / spot VMs for fault-tolerant training jobs. "
            "Set auto-pause on compute instances and auto-scale down to "
            "zero nodes when idle."
        ),
    },
    {
        "id": "bp_private_endpoints",
        "title": "Secure workspace with private endpoints",
        "category": "security",
        "priority": "high",
        "description": (
            "Deploy the Azure ML workspace behind a VNet with private "
            "endpoints for the workspace, storage, Key Vault and ACR."
        ),
    },
    {
        "id": "bp_experiment_tracking",
        "title": "Track every experiment run",
        "category": "mlops",
        "priority": "medium",
        "description": (
            "Log parameters, metrics and artifacts for every training "
            "run using Azure ML experiment tracking or MLflow integration."
        ),
    },
    {
        "id": "bp_cicd_pipelines",
        "title": "Automate model training and deployment",
        "category": "mlops",
        "priority": "medium",
        "description": (
            "Create CI/CD pipelines for automated retraining, evaluation "
            "gating and blue/green model deployment using Azure ML "
            "pipelines and GitHub Actions."
        ),
    },
    {
        "id": "bp_data_labeling",
        "title": "Use managed data labeling",
        "category": "data",
        "priority": "low",
        "description": (
            "Leverage Azure ML data labeling projects with ML-assisted "
            "labeling for faster annotation and quality control."
        ),
    },
]

_REFERENCE_ARCHITECTURES: list[dict[str, Any]] = [
    {
        "id": "small_team",
        "name": "Small Team ML Workspace",
        "description": (
            "A cost-effective setup for 1-5 data scientists doing "
            "experimentation and small-scale training."
        ),
        "team_size": "1-5",
        "use_case": "Experimentation, prototyping, small model training",
        "services": [
            "Azure ML Workspace",
            "Compute Instance (Standard_DS3_v2)",
            "Compute Cluster (Standard_NC4as_T4_v3, 0-2 nodes)",
            "Storage Account (Standard LRS)",
            "Key Vault",
            "Application Insights",
            "Container Registry (Basic)",
        ],
        "estimated_monthly_cost_usd": 500,
        "gpu_type": "T4",
        "mlops_level": "ad_hoc",
    },
    {
        "id": "enterprise_training",
        "name": "Enterprise Training Platform",
        "description": (
            "A production-grade ML platform for large teams with full "
            "MLOps, experiment tracking and automated retraining."
        ),
        "team_size": "20-50+",
        "use_case": "Large-scale training, full MLOps, model registry",
        "services": [
            "Azure ML Workspace (Private Endpoint)",
            "Compute Cluster (Standard_NC24ads_A100_v4, 0-8 nodes)",
            "Compute Instances (Standard_DS4_v2, per-user)",
            "Storage Account (ADLS Gen2, Premium)",
            "Key Vault (Premium)",
            "Application Insights",
            "Container Registry (Premium)",
            "Azure Databricks (optional)",
            "Azure OpenAI Service (optional)",
            "VNet with NSGs and private endpoints",
        ],
        "estimated_monthly_cost_usd": 15000,
        "gpu_type": "A100",
        "mlops_level": "full_mlops",
    },
    {
        "id": "realtime_inference",
        "name": "Real-Time Inference Platform",
        "description": (
            "Optimized for serving models at scale with low-latency "
            "managed online endpoints and auto-scaling."
        ),
        "team_size": "5-20",
        "use_case": "Production inference, API serving, model monitoring",
        "services": [
            "Azure ML Workspace (Private Endpoint)",
            "Managed Online Endpoints (Standard_NC4as_T4_v3)",
            "Compute Cluster (training, Standard_NC6s_v3, 0-4 nodes)",
            "Storage Account (ADLS Gen2)",
            "Key Vault",
            "Application Insights",
            "Container Registry (Standard)",
            "Azure Front Door (optional, global routing)",
            "Azure Monitor (autoscale metrics)",
        ],
        "estimated_monthly_cost_usd": 5000,
        "gpu_type": "T4",
        "mlops_level": "basic_cicd",
    },
]


class AiMlAccelerator:
    """AI/ML landing zone accelerator.

    Provides questionnaire questions, GPU SKU recommendations,
    architecture generation, sizing estimation and best-practice
    guidance tailored for machine learning workloads on Azure.
    """

    # ── Questionnaire ────────────────────────────────────────────────

    def get_questions(self) -> list[dict[str, Any]]:
        """Return AI/ML-specific questionnaire questions.

        Returns:
            List of question dicts for the questionnaire engine.
        """
        return list(_QUESTIONS)

    # ── SKU Recommendations ──────────────────────────────────────────

    def get_sku_recommendations(
        self, requirements: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """Return GPU SKU recommendations filtered by requirements.

        Args:
            requirements: Dict with optional keys ``gpu_type``,
                ``min_gpu_count``, ``price_tier``, ``use_case``.

        Returns:
            Filtered and sorted list of GPU SKU dicts.
        """
        skus = list(_GPU_SKU_CATALOG)
        gpu_type = requirements.get("gpu_type")
        if gpu_type:
            skus = [s for s in skus if s["gpu_type"] == gpu_type]
        min_gpus = requirements.get("min_gpu_count")
        if min_gpus is not None:
            skus = [s for s in skus if s["gpu_count"] >= min_gpus]
        tier = requirements.get("price_tier")
        if tier:
            skus = [s for s in skus if s["price_tier"] == tier]
        family = requirements.get("family")
        if family:
            skus = [s for s in skus if s["family"] == family]
        skus.sort(key=lambda s: s["gpu_memory_gb"], reverse=True)
        return skus

    # ── Architecture Generation ──────────────────────────────────────

    def generate_architecture(
        self, answers: dict[str, Any]
    ) -> dict[str, Any]:
        """Generate an AI/ML architecture from questionnaire answers.

        Args:
            answers: Dict of questionnaire answer values keyed by
                question ``id``.

        Returns:
            Architecture dict with ``services``, ``networking``,
            ``compute``, ``storage``, ``monitoring`` and ``optional``
            sections.
        """
        workload_type = answers.get("ml_workload_type", "both")
        gpu_req = answers.get("gpu_requirements", "single")
        data_vol = answers.get("data_volume", "medium")
        mlops = answers.get("mlops_maturity", "basic_cicd")
        realtime = answers.get("realtime_inference", False)
        optional_svcs = answers.get("optional_services", [])
        responsible = answers.get("responsible_ai", [])

        # Core services always present
        services: list[dict[str, Any]] = [
            {
                "name": "Azure Machine Learning Workspace",
                "type": "hub",
                "sku": "Enterprise",
            },
            {"name": "Key Vault", "type": "secrets", "sku": "Standard"},
            {
                "name": "Application Insights",
                "type": "monitoring",
                "sku": "Standard",
            },
            {
                "name": "Container Registry",
                "type": "container_registry",
                "sku": self._acr_sku(mlops),
            },
        ]

        # Compute
        compute = self._compute_config(
            workload_type, gpu_req, realtime
        )

        # Storage
        storage = self._storage_config(data_vol)
        services.append(storage["primary"])

        # Networking
        networking = {
            "private_endpoints": True,
            "vnet_integration": True,
            "nsg_rules": [
                "Allow AzureML control plane",
                "Allow storage private link",
                "Deny public internet to workspace",
            ],
        }

        # Optional services
        optional: list[dict[str, Any]] = []
        if "openai" in optional_svcs:
            optional.append(
                {"name": "Azure OpenAI Service", "type": "ai"}
            )
        if "cognitive_services" in optional_svcs:
            optional.append(
                {"name": "Azure Cognitive Services", "type": "ai"}
            )
        if "databricks" in optional_svcs:
            optional.append(
                {
                    "name": "Azure Databricks",
                    "type": "analytics",
                    "sku": "Premium",
                }
            )

        # Responsible AI config
        rai_config: dict[str, Any] = {}
        if isinstance(responsible, list):
            rai_config = {
                "fairness": "fairness" in responsible,
                "explainability": "explainability" in responsible,
                "privacy": "privacy" in responsible,
                "safety": "safety" in responsible,
            }

        return {
            "workload_type": workload_type,
            "services": services,
            "compute": compute,
            "storage": storage,
            "networking": networking,
            "monitoring": {
                "application_insights": True,
                "log_analytics": True,
                "model_monitoring": realtime,
            },
            "mlops": {"maturity": mlops},
            "responsible_ai": rai_config,
            "optional_services": optional,
        }

    # ── Best Practices ───────────────────────────────────────────────

    def get_best_practices(self) -> list[dict[str, Any]]:
        """Return AI/ML best-practice guidance.

        Returns:
            List of best-practice dicts with id, title, category,
            priority and description.
        """
        return list(_BEST_PRACTICES)

    # ── Sizing Estimation ────────────────────────────────────────────

    def estimate_sizing(
        self, requirements: dict[str, Any]
    ) -> dict[str, Any]:
        """Estimate resource sizing from workload requirements.

        Args:
            requirements: Dict with keys like ``data_volume``,
                ``gpu_requirements``, ``team_size``, ``ml_workload_type``.

        Returns:
            Sizing dict with compute, storage, networking estimates
            and monthly cost estimate.
        """
        gpu_req = requirements.get("gpu_requirements", "none")
        data_vol = requirements.get("data_volume", "small")
        team = requirements.get("team_size", "small")

        compute_sku, gpu_nodes = self._sizing_compute(gpu_req)
        storage_gb, storage_tier = self._sizing_storage(data_vol)
        instance_count = self._sizing_instances(team)

        monthly_cost = self._estimate_cost(
            compute_sku, gpu_nodes, storage_gb, instance_count
        )

        return {
            "compute_sku": compute_sku,
            "gpu_nodes_max": gpu_nodes,
            "compute_instances": instance_count,
            "storage_gb": storage_gb,
            "storage_tier": storage_tier,
            "estimated_monthly_cost_usd": monthly_cost,
        }

    # ── Architecture Validation ──────────────────────────────────────

    def validate_architecture(
        self, architecture: dict[str, Any]
    ) -> dict[str, Any]:
        """Validate an AI/ML architecture for completeness.

        Args:
            architecture: The full architecture dict to validate.

        Returns:
            Dict with ``valid``, ``errors``, ``warnings``,
            ``suggestions`` keys.
        """
        errors: list[str] = []
        warnings: list[str] = []
        suggestions: list[str] = []

        services = architecture.get("services", [])
        svc_names = [
            s.get("name", "") for s in services
            if isinstance(s, dict)
        ]

        # Required: ML Workspace
        if not any("Machine Learning" in n for n in svc_names):
            errors.append(
                "Architecture must include Azure Machine Learning Workspace."
            )

        # Required: Storage
        if not any(
            "Storage" in n or "Data Lake" in n for n in svc_names
        ):
            errors.append(
                "Architecture must include a Storage Account or "
                "Data Lake for ML data."
            )

        # Required: Key Vault
        if not any("Key Vault" in n for n in svc_names):
            warnings.append(
                "Key Vault is strongly recommended for secret management."
            )

        # Required: Container Registry
        if not any("Container Registry" in n for n in svc_names):
            warnings.append(
                "Container Registry is recommended for model image storage."
            )

        # Networking checks
        networking = architecture.get("networking", {})
        if not networking.get("private_endpoints"):
            warnings.append(
                "Private endpoints are recommended for production "
                "ML workspaces."
            )

        # Monitoring
        monitoring = architecture.get("monitoring", {})
        if not monitoring.get("application_insights"):
            suggestions.append(
                "Enable Application Insights for model monitoring "
                "and diagnostics."
            )

        # Compute checks
        compute = architecture.get("compute", {})
        if not compute.get("training_cluster") and not compute.get(
            "training_clusters"
        ):
            suggestions.append(
                "Consider adding a dedicated training compute cluster."
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
        }

    # ── Reference Architectures ──────────────────────────────────────

    def get_reference_architectures(self) -> list[dict[str, Any]]:
        """Return curated AI/ML reference architectures.

        Returns:
            List of three reference architecture dicts: small team,
            enterprise training and real-time inference.
        """
        return list(_REFERENCE_ARCHITECTURES)

    # ── Private Helpers ──────────────────────────────────────────────

    @staticmethod
    def _acr_sku(mlops: str) -> str:
        if mlops == "full_mlops":
            return "Premium"
        if mlops == "basic_cicd":
            return "Standard"
        return "Basic"

    @staticmethod
    def _compute_config(
        workload_type: str, gpu_req: str, realtime: bool
    ) -> dict[str, Any]:
        gpu_map = {
            "none": ("Standard_DS3_v2", 0),
            "single": ("Standard_NC4as_T4_v3", 2),
            "multi_gpu": ("Standard_NC24ads_A100_v4", 4),
            "multi_node": ("Standard_ND96asr_v4", 8),
        }
        sku, max_nodes = gpu_map.get(gpu_req, ("Standard_NC4as_T4_v3", 2))
        config: dict[str, Any] = {
            "training_cluster": {
                "vm_size": sku,
                "min_nodes": 0,
                "max_nodes": max_nodes,
            },
            "dev_instances": {"vm_size": "Standard_DS3_v2"},
        }
        if realtime or workload_type in ("inference", "both"):
            config["inference_cluster"] = {
                "vm_size": "Standard_NC4as_T4_v3",
                "instance_count": 2,
            }
        return config

    @staticmethod
    def _storage_config(data_vol: str) -> dict[str, Any]:
        tier_map = {
            "small": ("Standard_LRS", 256),
            "medium": ("Standard_LRS", 1024),
            "large": ("Premium_LRS", 4096),
            "very_large": ("Premium_LRS", 10240),
        }
        tier, gb = tier_map.get(data_vol, ("Standard_LRS", 1024))
        return {
            "primary": {
                "name": "Storage Account (ADLS Gen2)",
                "type": "storage",
                "sku": tier,
                "capacity_gb": gb,
                "hierarchical_namespace": True,
            },
            "model_artifacts": {
                "type": "blob",
                "sku": "Standard_LRS",
                "capacity_gb": max(gb // 4, 64),
            },
        }

    @staticmethod
    def _sizing_compute(gpu_req: str) -> tuple[str, int]:
        mapping: dict[str, tuple[str, int]] = {
            "none": ("Standard_DS3_v2", 0),
            "single": ("Standard_NC4as_T4_v3", 2),
            "multi_gpu": ("Standard_NC24ads_A100_v4", 4),
            "multi_node": ("Standard_ND96asr_v4", 8),
        }
        return mapping.get(gpu_req, ("Standard_NC4as_T4_v3", 2))

    @staticmethod
    def _sizing_storage(data_vol: str) -> tuple[int, str]:
        mapping: dict[str, tuple[int, str]] = {
            "small": (256, "Standard_LRS"),
            "medium": (1024, "Standard_LRS"),
            "large": (4096, "Premium_LRS"),
            "very_large": (10240, "Premium_LRS"),
        }
        return mapping.get(data_vol, (1024, "Standard_LRS"))

    @staticmethod
    def _sizing_instances(team: str) -> int:
        mapping = {"small": 2, "medium": 5, "large": 15, "enterprise": 30}
        return mapping.get(team, 2)

    @staticmethod
    def _estimate_cost(
        sku: str, nodes: int, storage_gb: int, instances: int
    ) -> int:
        base = 200  # workspace + monitoring baseline
        gpu_costs = {
            "Standard_DS3_v2": 150,
            "Standard_NC4as_T4_v3": 550,
            "Standard_NC24ads_A100_v4": 3500,
            "Standard_ND96asr_v4": 28000,
        }
        per_node = gpu_costs.get(sku, 550)
        compute_cost = per_node * max(nodes, 1)
        storage_cost = (storage_gb / 1024) * 20  # ~$20/TB/month
        instance_cost = instances * 120  # dev instance cost
        return int(base + compute_cost + storage_cost + instance_cost)


# Module-level singleton
aiml_accelerator = AiMlAccelerator()
