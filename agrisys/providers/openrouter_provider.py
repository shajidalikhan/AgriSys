"""OpenRouter Multi-Model Gateway Provider.

Fulfills §2.3: Access 200+ models with seamless fallback,
implementing BaseLLMProvider.
"""

from typing import Any, AsyncIterator, Dict, List, Optional
import json
import os
import httpx
from agrisys.providers.base import BaseLLMProvider


class OpenRouterProvider(BaseLLMProvider):
    """OpenRouter implementation of BaseLLMProvider with model fallback."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_model: str = "anthropic/claude-3.5-sonnet",
        fallback_model: str = "meta-llama/llama-3.3-70b-instruct",
        temperature: float = 0.1,
        max_tokens: int = 2048,
        timeout: float = 40.0,
    ) -> None:
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        self.default_model = default_model
        self.fallback_model = fallback_model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://agrisys.local",
            "X-Title": "AgriSys Agricultural Expert System",
        }

    async def complete(self, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        """Complete prompt, falling back to secondary model if primary fails."""
        models_to_try = [
            kwargs.get("model", self.default_model),
            self.fallback_model,
        ]

        last_err: Optional[Exception] = None
        for model in models_to_try:
            try:
                return await self._call_complete(model, messages, **kwargs)
            except Exception as e:
                last_err = e
                continue

        if last_err:
            raise last_err
        return ""

    async def _call_complete(self, model: str, messages: List[Dict[str, Any]], **kwargs: Any) -> str:
        url = f"{self.BASE_URL}/chat/completions"
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=self._get_headers(), json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"] or ""

    async def stream(self, messages: List[Dict[str, Any]], **kwargs: Any) -> AsyncIterator[str]:
        """Stream SSE chunks from OpenRouter."""
        url = f"{self.BASE_URL}/chat/completions"
        model = kwargs.get("model", self.default_model)
        payload = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", self.temperature),
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream("POST", url, headers=self._get_headers(), json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or not line.startswith("data:"):
                        continue
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data_str)
                        delta = chunk["choices"][0].get("delta", {}).get("content", "")
                        if delta:
                            yield delta
                    except json.JSONDecodeError:
                        continue

    @property
    def supports_vision(self) -> bool:
        """Claude 3.5 Sonnet, GPT-4o, and Gemini on OpenRouter support vision."""
        vision_keywords = ["claude-3", "gpt-4", "gemini", "vision"]
        return any(k in self.default_model.lower() for k in vision_keywords)

    @property
    def context_window(self) -> int:
        """Context window length for default model."""
        if "claude" in self.default_model.lower():
            return 200_000
        return 128_000
