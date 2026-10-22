"""Anthropic Claude API provider adapter."""

import json
import logging
import time
from typing import Any, Dict, Optional, Tuple, Type, TypeVar
from pydantic import BaseModel
from .base import BaseLLMAdapter
from ..config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class AnthropicAdapter(BaseLLMAdapter):
    """Adapter for Anthropic Claude models (Claude 3.5 Sonnet, Claude 3 Haiku)."""

    def __init__(self, model_name: str = "claude-3-5-sonnet-20240620", api_key: Optional[str] = None):
        super().__init__(model_name)
        settings = get_settings()
        self.api_key = api_key or settings.ANTHROPIC_API_KEY
        self._client = None

    def _get_client(self):
        if not self._client:
            from anthropic import AsyncAnthropic
            if not self.api_key:
                raise ValueError("ANTHROPIC_API_KEY is not configured in environment or .env")
            self._client = AsyncAnthropic(api_key=self.api_key)
        return self._client

    @property
    def provider_name(self) -> str:
        return "anthropic"

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Tuple[str, Dict[str, Any]]:
        client = self._get_client()
        t0 = time.perf_counter()
        response = await client.messages.create(
            model=self.model_name,
            system=system_prompt or "You are ORACLE, an advanced technical intelligence copilot.",
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency = int((time.perf_counter() - t0) * 1000)
        content = response.content[0].text if response.content else ""
        provenance = {
            "provider": self.provider_name,
            "model": self.model_name,
            "latency_ms": latency,
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        return content, provenance

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Tuple[T, Dict[str, Any]]:
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        full_system = (
            (system_prompt or "You are ORACLE, an advanced technical intelligence copilot.")
            + f"\nYou MUST reply ONLY with valid JSON matching the following schema:\n{schema_json}"
        )
        text, provenance = await self.generate_text(prompt, system_prompt=full_system, temperature=temperature)
        
        # Clean json backticks if wrapped
        clean_text = text.strip()
        if clean_text.startswith("```json"):
            clean_text = clean_text[7:]
        if clean_text.startswith("```"):
            clean_text = clean_text[3:]
        if clean_text.endswith("```"):
            clean_text = clean_text[:-3]

        data = json.loads(clean_text.strip())
        parsed = response_model.model_validate(data)
        return parsed, provenance
