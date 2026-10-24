"""OpenAI API provider adapter."""

import json
import logging
import time
from typing import Any, Dict, Optional, Tuple, Type, TypeVar
from pydantic import BaseModel
from .base import BaseLLMAdapter
from ..config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class OpenAIAdapter(BaseLLMAdapter):
    """Adapter for OpenAI models (GPT-4o, GPT-4o-mini)."""

    def __init__(self, model_name: str = "gpt-4o-mini", api_key: Optional[str] = None):
        super().__init__(model_name)
        settings = get_settings()
        self.api_key = api_key or settings.OPENAI_API_KEY
        self._client = None

    def _get_client(self):
        if not self._client:
            from openai import AsyncOpenAI
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY is not configured in environment or .env")
            self._client = AsyncOpenAI(api_key=self.api_key)
        return self._client

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Tuple[str, Dict[str, Any]]:
        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        t0 = time.perf_counter()
        response = await client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        latency = int((time.perf_counter() - t0) * 1000)

        content = response.choices[0].message.content or ""
        provenance = {
            "provider": self.provider_name,
            "model": self.model_name,
            "latency_ms": latency,
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        }
        return content, provenance

    async def stream_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ):
        client = self._get_client()
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        stream = await client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Tuple[T, Dict[str, Any]]:
        client = self._get_client()
        messages = []
        schema_json = json.dumps(response_model.model_json_schema(), indent=2)
        sys_msg = (
            (system_prompt or "You are ORACLE, a senior software architect and tech intelligence copilot.")
            + f"\nYou MUST respond strictly with valid JSON conforming to this schema:\n{schema_json}"
        )
        messages.append({"role": "system", "content": sys_msg})
        messages.append({"role": "user", "content": prompt})

        t0 = time.perf_counter()
        response = await client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        latency = int((time.perf_counter() - t0) * 1000)

        raw_json = response.choices[0].message.content or "{}"
        data = json.loads(raw_json)
        parsed = response_model.model_validate(data)

        provenance = {
            "provider": self.provider_name,
            "model": self.model_name,
            "latency_ms": latency,
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0,
        }
        return parsed, provenance
