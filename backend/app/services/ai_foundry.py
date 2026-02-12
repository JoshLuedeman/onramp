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
                "overall_score": 72.5,
                "frameworks": [{"name": "SOC2", "score": 72.5, "gaps": []}],
            })
        if "bicep" in prompt_lower:
            return "// Mock Bicep template\ntargetScope = 'subscription'\n"
        if "architecture" in prompt_lower or "landing zone" in prompt_lower:
            from app.services.archetypes import get_archetype
            return json.dumps(get_archetype("small"))
        return '{"status": "mock response", "message": "AI Foundry not configured"}'


# Singleton
ai_client = AIFoundryClient()
