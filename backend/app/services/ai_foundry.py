"""Azure AI Foundry client for LLM-powered architecture generation."""

import json
import logging
from typing import AsyncGenerator

from app.config import settings

logger = logging.getLogger(__name__)


class AIFoundryClient:
    """Client for Azure AI Foundry / OpenAI Service."""

    def __init__(self):
        self._client = None
        self._model = settings.ai_foundry_model

    async def _get_client(self):
        """Lazy-initialize the AI client."""
        if self._client is not None:
            return self._client

        if not settings.ai_foundry_endpoint:
            logger.warning("AI Foundry endpoint not configured, using mock responses")
            return None

        try:
            from azure.identity.aio import DefaultAzureCredential
            from azure.ai.projects.aio import AIProjectClient

            credential = DefaultAzureCredential()
            self._client = AIProjectClient(
                endpoint=settings.ai_foundry_endpoint,
                credential=credential,
            )
            return self._client
        except ImportError:
            logger.warning("Azure AI SDK not available, using mock responses")
            return None

    async def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Generate a completion from the AI model.

        Falls back to a mock response if AI Foundry is not configured.
        """
        client = await self._get_client()

        if client is None:
            return self._mock_completion(system_prompt, user_prompt)

        try:
            response = await client.inference.get_chat_completions(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI completion failed: {e}")
            raise

    async def generate_completion_stream(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """Stream a completion from the AI model."""
        client = await self._get_client()

        if client is None:
            yield self._mock_completion(system_prompt, user_prompt)
            return

        try:
            response = await client.inference.get_streaming_chat_completions(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            async for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"AI streaming failed: {e}")
            raise

    async def generate_architecture(self, questionnaire_answers: dict) -> dict:
        """Generate a landing zone architecture from questionnaire answers.

        This is the core AI function that transforms customer requirements
        into an Azure landing zone architecture.
        """
        system_prompt = self._get_architecture_system_prompt()
        user_prompt = self._format_architecture_request(questionnaire_answers)

        response = await self.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=8192,
        )

        try:
            # Extract JSON from the response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response[json_start:json_end])
            return json.loads(response)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse architecture JSON: {response[:200]}")
            return self._get_default_architecture()

    async def evaluate_compliance(
        self, architecture: dict, frameworks: list[str]
    ) -> dict:
        """Evaluate an architecture against compliance frameworks."""
        system_prompt = """You are an Azure compliance expert. Evaluate the given 
        architecture against the specified compliance frameworks. Return a JSON object 
        with compliance scores, gaps, and recommendations."""

        user_prompt = json.dumps({
            "architecture": architecture,
            "frameworks": frameworks,
        })

        response = await self.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=4096,
        )

        try:
            json_start = response.find("{")
            json_end = response.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                return json.loads(response[json_start:json_end])
            return json.loads(response)
        except json.JSONDecodeError:
            return {"score": 0, "status": "evaluation_failed", "gaps": [], "recommendations": []}

    async def generate_bicep(self, architecture: dict) -> str:
        """Generate Bicep templates from an architecture definition."""
        system_prompt = """You are an Azure Bicep expert. Generate production-ready 
        Bicep templates that implement the given architecture. Follow Azure best practices,
        use Azure Verified Modules where possible, and include proper parameterization."""

        user_prompt = f"Generate Bicep templates for this architecture:\n{json.dumps(architecture, indent=2)}"

        return await self.generate_completion(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=8192,
        )

    def _get_architecture_system_prompt(self) -> str:
        return """You are an expert Azure Solutions Architect specializing in the 
Azure Cloud Adoption Framework (CAF) and landing zone design. Your role is to 
analyze customer requirements and generate optimal landing zone architectures.

You must consider all 8 CAF design areas:
1. Azure Billing & Entra Tenant
2. Identity & Access Management
3. Resource Organization (management groups, subscriptions)
4. Network Topology & Connectivity
5. Security
6. Management & Monitoring
7. Governance
8. Platform Automation & DevOps

Return a JSON object with this structure:
{
    "organization_size": "small|medium|enterprise",
    "management_groups": { hierarchy definition },
    "subscriptions": [ subscription definitions ],
    "network_topology": { hub-spoke or vWAN definition },
    "identity": { identity configuration },
    "security": { security controls },
    "governance": { policy assignments },
    "management": { monitoring and management config },
    "compliance_frameworks": [ applied frameworks ],
    "recommendations": [ list of recommendations ],
    "estimated_monthly_cost_usd": number
}"""

    def _format_architecture_request(self, answers: dict) -> str:
        return f"""Based on these customer requirements, design an Azure landing zone:

{json.dumps(answers, indent=2)}

Generate a complete landing zone architecture as a JSON object."""

    def _mock_completion(self, system_prompt: str, user_prompt: str) -> str:
        """Return a mock response for development without AI Foundry."""
        return json.dumps(self._get_default_architecture())

    def _get_default_architecture(self) -> dict:
        """Return a sensible default architecture for development/fallback."""
        return {
            "organization_size": "medium",
            "management_groups": {
                "root": {
                    "name": "Tenant Root Group",
                    "children": {
                        "platform": {
                            "name": "Platform",
                            "children": {
                                "identity": {"name": "Identity"},
                                "management": {"name": "Management"},
                                "connectivity": {"name": "Connectivity"},
                            },
                        },
                        "landing_zones": {
                            "name": "Landing Zones",
                            "children": {
                                "corp": {"name": "Corp"},
                                "online": {"name": "Online"},
                            },
                        },
                        "sandbox": {"name": "Sandbox"},
                        "decommissioned": {"name": "Decommissioned"},
                    },
                }
            },
            "subscriptions": [
                {
                    "name": "sub-platform-identity",
                    "purpose": "Identity services",
                    "management_group": "identity",
                },
                {
                    "name": "sub-platform-management",
                    "purpose": "Management & monitoring",
                    "management_group": "management",
                },
                {
                    "name": "sub-platform-connectivity",
                    "purpose": "Hub networking",
                    "management_group": "connectivity",
                },
                {
                    "name": "sub-lz-corp-001",
                    "purpose": "Corp workloads",
                    "management_group": "corp",
                },
            ],
            "network_topology": {
                "type": "hub-spoke",
                "hub": {"vnet_cidr": "10.0.0.0/16", "region": "eastus2"},
                "spokes": [
                    {"name": "identity", "vnet_cidr": "10.1.0.0/16"},
                    {"name": "corp-001", "vnet_cidr": "10.10.0.0/16"},
                ],
            },
            "identity": {
                "provider": "Microsoft Entra ID",
                "rbac_model": "Azure RBAC",
                "pim_enabled": True,
                "conditional_access": True,
            },
            "security": {
                "defender_for_cloud": True,
                "sentinel": True,
                "ddos_protection": False,
                "key_vault_per_subscription": True,
            },
            "governance": {
                "tagging_strategy": {
                    "mandatory_tags": ["Environment", "CostCenter", "Owner", "Application"]
                },
                "naming_convention": "Azure CAF recommended",
                "cost_management": True,
            },
            "management": {
                "log_analytics_workspace": True,
                "update_management": True,
                "backup_policy": True,
                "retention_days": 90,
            },
            "compliance_frameworks": [],
            "recommendations": [
                "Enable Microsoft Defender for Cloud on all subscriptions",
                "Configure PIM for privileged role assignments",
                "Deploy hub-spoke network topology with Azure Firewall",
                "Implement mandatory tagging policy at management group level",
            ],
            "estimated_monthly_cost_usd": 2500,
        }


# Singleton instance
ai_client = AIFoundryClient()
