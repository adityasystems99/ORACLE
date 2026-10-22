"""Abstract Base Class for provider-independent LLM adapters."""

import abc
from typing import Any, Dict, Optional, Tuple, Type, TypeVar
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class BaseLLMAdapter(abc.ABC):
    """Protocol for pluggable LLM backends (OpenAI, Anthropic, Ollama, Mock)."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @property
    @abc.abstractmethod
    def provider_name(self) -> str:
        """Identifier for the LLM provider."""
        pass

    @abc.abstractmethod
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Tuple[str, Dict[str, Any]]:
        """Generate unstructured markdown/text response with provenance metadata."""
        pass

    @abc.abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Tuple[T, Dict[str, Any]]:
        """Generate validated Pydantic object from LLM response with provenance metadata."""
        pass
