"""OpenRouter client wrapper implementing the shared LLM interface."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import requests

from .base_client import BaseLLMClient, LLMResult


class OpenRouterError(RuntimeError):
    """Custom error raised for OpenRouter specific failures."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        response: Optional[Any] = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class OpenRouterClient(BaseLLMClient):
    """HTTP client for interacting with OpenRouter chat completions API."""

    def __init__(
        self,
        api_key: str,
        model_name: str,
        *,
        base_url: str = "https://openrouter.ai/api/v1/chat/completions",
        http_referer: str = "https://market-news.local/",
        app_title: str = "Market News Automation",
        default_timeout: int = 180,
        session: Optional[requests.Session] = None,
    ) -> None:
        if not api_key:
            raise ValueError("OpenRouter APIキーが設定されていません")

        super().__init__(provider="openrouter", model_name=model_name)
        self.logger = logging.getLogger(__name__)
        self.api_key = api_key
        self.base_url = base_url
        self.http_referer = http_referer
        self.app_title = app_title
        self.default_timeout = default_timeout
        self.session = session or requests.Session()

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_output_tokens: Optional[int] = None,
        timeout: Optional[int] = None,
        response_format: Optional[Dict[str, Any]] = None,
        **_: Any,
    ) -> LLMResult:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload: Dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "temperature": temperature,
        }
        if max_output_tokens:
            payload["max_tokens"] = max_output_tokens
        if response_format:
            payload["response_format"] = response_format

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.http_referer,
            "X-Title": self.app_title,
        }

        try:
            response = self.session.post(
                self.base_url,
                json=payload,
                headers=headers,
                timeout=timeout or self.default_timeout,
            )
        except requests.Timeout as exc:
            raise TimeoutError("OpenRouterリクエストがタイムアウトしました") from exc
        except requests.RequestException as exc:
            raise OpenRouterError(f"OpenRouterリクエストに失敗しました: {exc}") from exc

        if response.status_code >= 400:
            message = f"OpenRouter APIエラー: {response.status_code} {response.text}"
            if response.status_code == 429:
                message = "OpenRouter rate limit (status 429)"
            raise OpenRouterError(
                message,
                status_code=response.status_code,
                response=response.text,
            )

        try:
            data = response.json()
        except ValueError as exc:
            raise OpenRouterError("OpenRouter APIレスポンスのJSON解析に失敗しました") from exc

        choices = data.get("choices") or []
        if not choices:
            raise OpenRouterError("OpenRouter APIレスポンスにchoicesが含まれていません", response=data)

        first_choice = choices[0]
        message = first_choice.get("message", {})
        text = (message.get("content") or "").strip()
        if not text:
            raise OpenRouterError("OpenRouter APIレスポンスにテキストが含まれていません", response=data)

        metadata: Dict[str, Any] = {
            "id": data.get("id"),
            "model": data.get("model", self.model_name),
        }
        if "usage" in data:
            metadata["usage"] = data["usage"]

        return LLMResult(text=text, metadata=metadata, raw_response=data)
