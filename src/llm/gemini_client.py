"""Gemini client wrapper implementing the shared LLM interface."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import google.generativeai as genai

from .base_client import BaseLLMClient, LLMResult


class GeminiClient(BaseLLMClient):
    """Wrapper around google-generativeai models."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        *,
        default_timeout: int = 600,
        default_safety_settings: Optional[Dict[Any, Any]] = None,
    ) -> None:
        if not api_key:
            raise ValueError("Gemini APIキーが設定されていません")

        super().__init__(provider="gemini", model_name=model_name)
        self.logger = logging.getLogger(__name__)
        self.default_timeout = default_timeout

        try:
            genai.configure(api_key=api_key)
        except Exception as exc:  # pragma: no cover - network failure is environment specific
            self.logger.error("Gemini APIの初期化に失敗しました: %s", exc)
            raise

        self.model = genai.GenerativeModel(model_name)
        self.default_safety_settings = default_safety_settings or {
            genai.types.HarmCategory.HARM_CATEGORY_HARASSMENT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            genai.types.HarmCategory.HARM_CATEGORY_HATE_SPEECH: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            genai.types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            genai.types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: genai.types.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        }

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
        combined_prompt = prompt if not system_prompt else f"{system_prompt.strip()}\n\n{prompt.strip()}"
        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_output_tokens or 1024,
            temperature=temperature,
        )
        request_options = {"timeout": timeout or self.default_timeout}
        safety_settings = kwargs.get("safety_settings") or self.default_safety_settings

        try:
            response = self.model.generate_content(
                combined_prompt,
                generation_config=generation_config,
                safety_settings=safety_settings,
                request_options=request_options,
            )
        except Exception as exc:  # pragma: no cover - depends on API responses
            raise RuntimeError(str(exc)) from exc

        text = getattr(response, "text", "").strip()
        if not text:
            raise RuntimeError("Gemini APIレスポンスにテキストが含まれていません")

        metadata: Dict[str, Any] = {"model": self.model_name}
        if hasattr(response, "candidates") and response.candidates:
            candidate = response.candidates[0]
            metadata["finish_reason"] = getattr(candidate, "finish_reason", None)
            if hasattr(candidate, "safety_ratings") and candidate.safety_ratings:
                metadata["safety_ratings"] = [
                    {
                        "category": rating.category,
                        "probability": getattr(rating, "probability", None),
                    }
                    for rating in candidate.safety_ratings
                ]

        return LLMResult(text=text, metadata=metadata, raw_response=response)
