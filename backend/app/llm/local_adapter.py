"""Local LLM adapter connecting to local inference engines (Ollama, vLLM, LMStudio)."""

import json
import logging
import time
from typing import Any, Dict, Optional, Tuple, Type, TypeVar
import httpx
from pydantic import BaseModel
from .base import BaseLLMAdapter
from ..config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T", bound=BaseModel)


class LocalLLMAdapter(BaseLLMAdapter):
    """Adapter for locally hosted models via Ollama or OpenAI-compatible local servers."""

    def __init__(self, model_name: str = "llama3:latest", base_url: Optional[str] = None):
        super().__init__(model_name)
        settings = get_settings()
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")

    @property
    def provider_name(self) -> str:
        return "ollama-local"

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Tuple[str, Dict[str, Any]]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "system": system_prompt or "You are ORACLE, an advanced technical intelligence copilot.",
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }

        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()

        latency = int((time.perf_counter() - t0) * 1000)
        content = data.get("response", "")
        provenance = {
            "provider": self.provider_name,
            "model": self.model_name,
            "endpoint": self.base_url,
            "latency_ms": latency,
            "prompt_eval_count": data.get("prompt_eval_count", 0),
            "eval_count": data.get("eval_count", 0),
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
        clean = text.strip()
        if clean.startswith("```json"):
            clean = clean[7:]
        if clean.startswith("```"):
            clean = clean[3:]
        if clean.endswith("```"):
            clean = clean[:-3]

        data = json.loads(clean.strip())
        parsed = response_model.model_validate(data)
        return parsed, provenance
