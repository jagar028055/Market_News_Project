"""Base interfaces for LLM clients used across the project."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class LLMResult:
    """Container for normalised responses from different LLM providers."""

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    raw_response: Any = None


class BaseLLMClient(ABC):
    """Abstract base class for LLM clients."""

    provider: str
    model_name: str

    def __init__(self, provider: str, model_name: str) -> None:
        self.provider = provider
        self.model_name = model_name

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResult:
        """Generate text from the model and return a normalised result."""

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"{self.__class__.__name__}(provider={self.provider!r}, model_name={self.model_name!r})"
