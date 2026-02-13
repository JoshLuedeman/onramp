"""Azure AI Foundry client for architecture generation and evaluation."""

import json
import logging
from typing import Optional, AsyncGenerator

from app.config import settings

logger = logging.getLogger(__name__)


class AIFoundryClient:
    """Client for Azure AI Foundry model interactions."""

    def __init__(self):
        self._client = None
        self._async_client = None

    @property
    def is_configured(self) -> bool:
        return bool(settings.ai_foundry_endpoint and settings.ai_foundry_key)

    def _get_client(self):
        """Get synchronous OpenAI-compatible client."""
        if self._client is None and self.is_configured:
            try:
                from openai import AzureOpenAI
                self._client = AzureOpenAI(
                    azure_endpoint=settings.ai_foundry_endpoint,
                    api_key=settings.ai_foundry_key,
                    api_version="2024-06-01",
                )
            except ImportError:
                logger.warning("openai package not installed — using mock mode")
            except Exception as e:
                logger.warning(f"Failed to initialize AI client: {e}")
        return self._client

    def _get_async_client(self):
        """Get async OpenAI-compatible client."""
        if self._async_client is None and self.is_configured:
            try:
                from openai import AsyncAzureOpenAI
                self._async_client = AsyncAzureOpenAI(
                    azure_endpoint=settings.ai_foundry_endpoint,
                    api_key=settings.ai_foundry_key,
                    api_version="2024-06-01",
                )
            except ImportError:
                logger.warning("openai package not installed — using mock mode")
            except Exception as e:
                logger.warning(f"Failed to initialize async AI client: {e}")
        return self._async_client

    def generate_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        model: Optional[str] = None,
    ) -> str:
        """Generate a completion using Azure AI Foundry."""
        client = self._get_client()
        if client is None:
            logger.info("AI not configured — returning mock completion")
            return self._mock_completion(system_prompt, user_prompt)

        deployment = model or settings.ai_foundry_deployment or "gpt-4o"
        try:
            response = client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                response_format={"type": "json_object"} if "json" in system_prompt.lower()[:200] else None,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI completion failed: {e}")
            return self._mock_completion(system_prompt, user_prompt)

    async def generate_completion_async(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        model: Optional[str] = None,
    ) -> str:
        """Generate a completion asynchronously."""
        client = self._get_async_client()
        if client is None:
            return self._mock_completion(system_prompt, user_prompt)

        deployment = model or settings.ai_foundry_deployment or "gpt-4o"
        try:
            response = await client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Async AI completion failed: {e}")
            return self._mock_completion(system_prompt, user_prompt)

    async def stream_completion(
        self,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        model: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """Stream a completion token by token."""
        client = self._get_async_client()
        if client is None:
            # Mock streaming
            mock = self._mock_completion(system_prompt, user_prompt)
            for word in mock.split():
                yield word + " "
            return

        deployment = model or settings.ai_foundry_deployment or "gpt-4o"
        try:
            stream = await client.chat.completions.create(
                model=deployment,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Stream failed: {e}")
            yield f"Error: {str(e)}"

    async def generate_architecture(self, answers: dict) -> dict:
        """Generate a landing zone architecture from questionnaire answers."""
        from app.services.prompts import (
            ARCHITECTURE_SYSTEM_PROMPT,
            build_architecture_prompt,
        )

        user_prompt = build_architecture_prompt(answers)
        response = self.generate_completion(
            ARCHITECTURE_SYSTEM_PROMPT, user_prompt, temperature=0.2
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            logger.warning("AI response was not valid JSON, using archetype fallback")
            from app.services.archetypes import get_archetype_for_answers
            return get_archetype_for_answers(answers)

    async def evaluate_compliance(self, architecture: dict, frameworks: list[str]) -> dict:
        """Evaluate architecture compliance using AI."""
        from app.services.prompts import COMPLIANCE_EVALUATION_PROMPT

        user_prompt = json.dumps(
            {"architecture": architecture, "frameworks": frameworks}, indent=2
        )
        response = self.generate_completion(
            COMPLIANCE_EVALUATION_PROMPT, user_prompt, temperature=0.1
        )

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"error": "Failed to parse compliance evaluation", "raw": response}

    async def generate_bicep(self, architecture: dict) -> str:
        """Generate Bicep templates using AI."""
        from app.services.prompts import BICEP_GENERATION_PROMPT

        user_prompt = json.dumps(architecture, indent=2)
        return self.generate_completion(
            BICEP_GENERATION_PROMPT, user_prompt, temperature=0.1, max_tokens=8192
        )

    def _mock_completion(self, system_prompt: str, user_prompt: str) -> str:
        """Return mock responses for development mode."""
        prompt_lower = system_prompt.lower()
        if "compliance" in prompt_lower and "evaluate" in prompt_lower:
            return json.dumps({
                "overall_score": 68,
                "frameworks": [
                    {
                        "name": "SOC2",
                        "score": 75,
                        "status": "partially_compliant",
                        "controls_met": 9,
                        "controls_partial": 2,
                        "controls_gap": 1,
                        "gaps": [
                            {
                                "control_id": "SOC2-CC6.1",
                                "control_name": "Logical and Physical Access Controls",
                                "severity": "high",
                                "status": "gap",
                                "gap_description": "Privileged Identity Management (PIM) is not enabled for just-in-time access to critical resources",
                                "remediation": "Enable Azure AD PIM for all privileged roles and configure activation approval workflows",
                            },
                            {
                                "control_id": "SOC2-CC7.2",
                                "control_name": "System Monitoring",
                                "severity": "medium",
                                "status": "partial",
                                "gap_description": "Microsoft Sentinel is not enabled for centralized security monitoring and alerting",
                                "remediation": "Deploy Microsoft Sentinel workspace and configure analytics rules for key threat scenarios",
                            },
                        ],
                    },
                    {
                        "name": "NIST-800-53",
                        "score": 62,
                        "status": "partially_compliant",
                        "controls_met": 8,
                        "controls_partial": 3,
                        "controls_gap": 2,
                        "gaps": [
                            {
                                "control_id": "NIST-AC-2",
                                "control_name": "Account Management",
                                "severity": "high",
                                "status": "gap",
                                "gap_description": "No automated account lifecycle management or periodic access reviews configured",
                                "remediation": "Configure Azure AD Access Reviews for all privileged and guest accounts with quarterly review cycles",
                            },
                            {
                                "control_id": "NIST-AU-6",
                                "control_name": "Audit Review, Analysis, and Reporting",
                                "severity": "medium",
                                "status": "partial",
                                "gap_description": "Log Analytics workspace exists but lacks cross-workspace correlation and automated alerting",
                                "remediation": "Enable diagnostic settings for all resources and configure Azure Monitor alert rules for critical events",
                            },
                            {
                                "control_id": "NIST-IR-4",
                                "control_name": "Incident Handling",
                                "severity": "high",
                                "status": "gap",
                                "gap_description": "No automated incident response playbooks configured",
                                "remediation": "Deploy Microsoft Sentinel with automated playbooks for common incident types using Logic Apps",
                            },
                        ],
                    },
                ],
                "top_recommendations": [
                    "Enable Azure AD PIM for just-in-time privileged access across all subscriptions",
                    "Deploy Microsoft Sentinel for centralized SIEM and SOAR capabilities",
                    "Configure automated access reviews for privileged and guest accounts",
                    "Enable diagnostic settings for all Azure resources to Log Analytics",
                    "Implement automated incident response playbooks with Logic Apps",
                ],
            })
        if "bicep" in prompt_lower:
            return json.dumps({
                "main.bicep": "targetScope = 'subscription'\n\n@description('Primary Azure region')\nparam location string = 'eastus2'\n\n@description('Environment name')\nparam environment string = 'prod'\n\nvar tags = {\n  managedBy: 'OnRamp'\n  environment: environment\n}\n\nmodule managementGroups 'modules/management-groups.bicep' = {\n  name: 'management-groups'\n  scope: tenant()\n}\n\nresource rgNetworking 'Microsoft.Resources/resourceGroups@2024-03-01' = {\n  name: 'rg-networking-${environment}'\n  location: location\n  tags: tags\n}\n\nmodule networking 'modules/networking.bicep' = {\n  scope: rgNetworking\n  name: 'hub-spoke-networking'\n  params: {\n    location: location\n    tags: tags\n  }\n}\n\nresource rgSecurity 'Microsoft.Resources/resourceGroups@2024-03-01' = {\n  name: 'rg-security-${environment}'\n  location: location\n  tags: tags\n}\n\nmodule policyAssignments 'modules/policy-assignments.bicep' = {\n  name: 'policy-assignments'\n  params: {\n    environment: environment\n  }\n}\n",
                "modules/management-groups.bicep": "targetScope = 'tenant'\n\n@description('Top-level management group name')\nparam topLevelMgName string = 'Organization'\n\nresource topLevelMg 'Microsoft.Management/managementGroups@2023-04-01' = {\n  name: topLevelMgName\n  properties: {\n    displayName: topLevelMgName\n  }\n}\n\nresource platformMg 'Microsoft.Management/managementGroups@2023-04-01' = {\n  name: '${topLevelMgName}-Platform'\n  properties: {\n    displayName: 'Platform'\n    details: {\n      parent: {\n        id: topLevelMg.id\n      }\n    }\n  }\n}\n\nresource landingZonesMg 'Microsoft.Management/managementGroups@2023-04-01' = {\n  name: '${topLevelMgName}-LandingZones'\n  properties: {\n    displayName: 'Landing Zones'\n    details: {\n      parent: {\n        id: topLevelMg.id\n      }\n    }\n  }\n}\n\noutput topLevelMgId string = topLevelMg.id\n",
                "modules/networking.bicep": "// Hub-spoke networking module\n\n@description('Azure region for resources')\nparam location string\n\n@description('Hub VNET CIDR')\nparam hubCidr string = '10.0.0.0/16'\n\n@description('Resource tags')\nparam tags object = {}\n\nresource hubVnet 'Microsoft.Network/virtualNetworks@2024-01-01' = {\n  name: 'vnet-hub'\n  location: location\n  tags: tags\n  properties: {\n    addressSpace: {\n      addressPrefixes: [\n        hubCidr\n      ]\n    }\n    subnets: [\n      {\n        name: 'AzureFirewallSubnet'\n        properties: {\n          addressPrefix: cidrSubnet(hubCidr, 26, 0)\n        }\n      }\n      {\n        name: 'AzureBastionSubnet'\n        properties: {\n          addressPrefix: cidrSubnet(hubCidr, 26, 1)\n        }\n      }\n    ]\n  }\n}\n\noutput hubVnetId string = hubVnet.id\n",
                "modules/policy-assignments.bicep": "// Azure Policy assignments for governance\n\n@description('Environment name')\nparam environment string\n\ntargetScope = 'managementGroup'\n\nresource allowedLocations 'Microsoft.Authorization/policyAssignments@2024-04-01' = {\n  name: 'allowed-locations-${environment}'\n  properties: {\n    displayName: 'Allowed Locations'\n    policyDefinitionId: '/providers/Microsoft.Authorization/policyDefinitions/e56962a6-4747-49cd-b67b-bf8b01975c4c'\n    parameters: {\n      listOfAllowedLocations: {\n        value: [\n          'eastus2'\n          'centralus'\n        ]\n      }\n    }\n  }\n}\n",
                "parameters/env.bicepparam": "using './main.bicep'\n\nparam location = 'eastus2'\nparam environment = 'prod'\n"
            })
        if "architecture" in prompt_lower or "landing zone" in prompt_lower:
            from app.services.archetypes import get_archetype_for_answers
            # Parse answers from user_prompt if possible; fall back to small archetype
            try:
                answers = {}
                for line in user_prompt.splitlines():
                    line = line.strip()
                    if line.startswith("- ") and ": " in line:
                        k, v = line[2:].split(": ", 1)
                        answers[k] = v
                return json.dumps(get_archetype_for_answers(answers))
            except Exception:
                from app.services.archetypes import get_archetype
                return json.dumps(get_archetype("small"))
        return '{"status": "mock response", "message": "AI Foundry not configured"}'


# Singleton
ai_client = AIFoundryClient()
