"""Secure Remote Model Endpoint Tool for Crop Recommendation."""

from __future__ import annotations
import logging
from typing import Any
import httpx
from agrisys.agents.crop.models import CropInputFeatures
from agrisys.agents.crop.registry import BaseCropModelTool, register_crop_tool

logger = logging.getLogger(__name__)


class EndpointCropModelTool(BaseCropModelTool):
    """SRP: Connects to remote crop recommendation model server over secure HTTP/REST."""

    def __init__(
        self,
        endpoint_url: str,
        auth_token: str | None = None,
        timeout_seconds: float = 4.0,
        tool_name: str = "endpoint_crop_tool",
    ):
        self.endpoint_url = endpoint_url
        self.auth_token = auth_token
        self.timeout_seconds = timeout_seconds
        self._tool_name = tool_name
        self.circuit_open = False
        self.consecutive_failures = 0

    @property
    def tool_name(self) -> str:
        return self._tool_name

    async def predict(self, features: CropInputFeatures) -> list[tuple[str, float]]:
        if self.circuit_open:
            logger.warning(f"Circuit breaker OPEN for {self.endpoint_url}. Tripping to local fallback.")
            raise ConnectionError(f"Circuit breaker is OPEN for {self.endpoint_url}")

        headers = {"Content-Type": "application/json"}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        payload = {
            "N": features.N,
            "P": features.P,
            "K": features.K,
            "temperature": features.temperature,
            "humidity": features.humidity,
            "ph": features.ph,
            "rainfall": features.rainfall,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                resp = await client.post(self.endpoint_url, json=payload, headers=headers)
                resp.raise_for_status()
                data = resp.json()

                # Expect list of {"crop": "...", "probability": 0.85} or similar
                ranked: list[tuple[str, float]] = []
                if isinstance(data, list):
                    for item in data:
                        c = item.get("crop") or item.get("label")
                        p = float(item.get("probability", item.get("score", 0.0)))
                        if c:
                            ranked.append((str(c), p))
                elif isinstance(data, dict) and "predictions" in data:
                    for item in data["predictions"]:
                        ranked.append((str(item["crop"]), float(item["probability"])))

                self.consecutive_failures = 0
                return ranked
        except Exception as e:
            self.consecutive_failures += 1
            if self.consecutive_failures >= 3:
                self.circuit_open = True
                logger.error(f"Circuit breaker TRIPPED for {self.endpoint_url} after {self.consecutive_failures} failures.")
            raise RuntimeError(f"Remote crop model call failed: {e}")
