"""LLM Adapter Factory resolving configured provider."""

import logging
from typing import Optional
from .anthropic_adapter import AnthropicAdapter
from .base import BaseLLMAdapter
from .local_adapter import LocalLLMAdapter
from .mock_adapter import MockLLMAdapter
from .openai_adapter import OpenAIAdapter
from ..config import get_settings

logger = logging.getLogger(__name__)


def get_llm_adapter(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
) -> BaseLLMAdapter:
    """Factory resolving appropriate LLM adapter with fallback to mock if unconfigured."""
    settings = get_settings()
    selected_provider = (provider or settings.LLM_PROVIDER).lower()
    selected_model = model_name or settings.LLM_MODEL

    if selected_provider == "openai":
        if settings.OPENAI_API_KEY:
            return OpenAIAdapter(model_name=selected_model)
        logger.warning("OPENAI_API_KEY missing; falling back to MockLLMAdapter.")
        return MockLLMAdapter(model_name=selected_model)

    if selected_provider == "anthropic":
        if settings.ANTHROPIC_API_KEY:
            return AnthropicAdapter(model_name=selected_model)
        logger.warning("ANTHROPIC_API_KEY missing; falling back to MockLLMAdapter.")
        return MockLLMAdapter(model_name=selected_model)

    if selected_provider in ["ollama", "local"]:
        return LocalLLMAdapter(model_name=selected_model, base_url=settings.OLLAMA_BASE_URL)

    # Default to mock adapter
    return MockLLMAdapter(model_name=selected_model)
