"""Explicit mock adapter for testing and deterministic offline development."""

import json
import time
from typing import Any, Dict, List, Optional, Tuple, Type, TypeVar
from pydantic import BaseModel
from .base import BaseLLMAdapter

T = TypeVar("T", bound=BaseModel)


class MockLLMAdapter(BaseLLMAdapter):
    """Explicitly identified offline testing adapter.

    WARNING: Used exclusively for local offline testing and CI environments.
    Metadata clearly labels all outputs as mock-generated.
    """

    @property
    def provider_name(self) -> str:
        return "mock-test"

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048,
    ) -> Tuple[str, Dict[str, Any]]:
        provenance = {
            "provider": self.provider_name,
            "model": self.model_name,
            "is_mock_provider": True,
            "warning": "Generated via offline test adapter; do not present as external LLM output.",
            "latency_ms": 12,
        }
        text = (
            f"### ORACLE Intelligence Impact Assessment [MOCK PROVIDER]\n\n"
            f"**Evaluation Summary:** Analyzed event and dependencies.\n\n"
            f"- Evidence verified from primary source.\n"
            f"- Graph blast radius confirms impacted components.\n"
            f"- Recommended action: Review version constraints and test suite."
        )
        return text, provenance

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> Tuple[T, Dict[str, Any]]:
        provenance = {
            "provider": self.provider_name,
            "model": self.model_name,
            "is_mock_provider": True,
            "warning": "Generated via offline test adapter; do not present as external LLM output.",
            "latency_ms": 15,
        }

        # Dynamically build realistic structured data matching response_model fields
        fields = response_model.model_fields
        data: Dict[str, Any] = {}

        if "executive_summary" in fields:
            data["executive_summary"] = (
                "Automated intelligence analysis detected an ecosystem change. "
                "Immediate mitigation steps have been prepared based on dependency blast radius."
            )
        if "technical_root_cause" in fields:
            data["technical_root_cause"] = (
                "A breaking interface modification or security disclosure was identified in upstream release manifests. "
                "Downstream packages with unpinned version ranges or direct dependency links are susceptible."
            )
        if "breaking_changes" in fields:
            data["breaking_changes"] = [
                "Modification of public API parameter signatures",
                "Deprecation of legacy serialization schema attributes",
            ]
        if "mitigation_playbook" in fields:
            data["mitigation_playbook"] = [
                {
                    "step_number": 1,
                    "title": "Audit and Pin Direct Dependency Versions",
                    "description": "Lock versions in pyproject.toml / requirements.txt to prevent unexpected upstream updates.",
                    "priority": "high",
                    "action_type": "config_change",
                    "code_or_command": "pip install --upgrade -r requirements.txt --dry-run",
                    "verification_check": "pytest tests/ -v",
                    "estimated_effort": "low",
                },
                {
                    "step_number": 2,
                    "title": "Execute Compatibility Test Suite",
                    "description": "Run automated integration tests against the newly released version in an isolated environment.",
                    "priority": "medium",
                    "action_type": "code_refactor",
                    "code_or_command": "pytest --import-mode=importlib",
                    "verification_check": "Ensure zero deprecation warnings in CI output",
                    "estimated_effort": "medium",
                },
            ]
        if "confidence_score" in fields:
            data["confidence_score"] = 0.88

        instance = response_model.model_validate(data)
        return instance, provenance
