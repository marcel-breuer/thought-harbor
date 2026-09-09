"""Small async HTTP transport shared by vendor-specific adapters."""

import asyncio
from collections.abc import Mapping
from typing import Any

import httpx

from thoughtharbor.ai.errors import ProviderError
from thoughtharbor.ai.settings import CapabilitySettings


class HTTPProvider:
    """Implement timeout and bounded retry policy without leaking HTTP details."""

    provider_name: str

    def __init__(
        self,
        settings: CapabilitySettings,
        *,
        provider_name: str,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.settings = settings
        self.provider_name = provider_name
        self._transport = transport

    async def post(self, path: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        """POST JSON with bounded retries for transient provider failures."""

        if not self.settings.base_url:
            raise ProviderError(
                self.provider_name,
                "configuration",
                f"No base URL configured for {self.provider_name}",
            )

        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"

        async with httpx.AsyncClient(
            base_url=self.settings.base_url,
            headers=headers,
            timeout=self.settings.timeout_seconds,
            transport=self._transport,
        ) as client:
            for attempt in range(self.settings.max_retries + 1):
                try:
                    response = await client.post(path, json=dict(payload))
                except httpx.TimeoutException as error:
                    if attempt < self.settings.max_retries:
                        await self._wait(attempt)
                        continue
                    raise ProviderError(
                        self.provider_name,
                        "timeout",
                        f"{self.provider_name} timed out after {attempt + 1} attempts",
                        retryable=True,
                    ) from error
                except httpx.NetworkError as error:
                    if attempt < self.settings.max_retries:
                        await self._wait(attempt)
                        continue
                    raise ProviderError(
                        self.provider_name,
                        "unavailable",
                        f"{self.provider_name} could not be reached",
                        retryable=True,
                    ) from error

                if response.status_code in {408, 429} or response.status_code >= 500:
                    if attempt < self.settings.max_retries:
                        await self._wait(attempt)
                        continue
                    code = "rate_limited" if response.status_code == 429 else "unavailable"
                    raise ProviderError(
                        self.provider_name,
                        code,
                        f"{self.provider_name} returned HTTP {response.status_code}",
                        retryable=True,
                    )

                if response.status_code in {401, 403}:
                    raise ProviderError(
                        self.provider_name,
                        "authentication",
                        f"{self.provider_name} rejected the configured credentials",
                    )
                if response.status_code >= 400:
                    raise ProviderError(
                        self.provider_name,
                        "request_failed",
                        f"{self.provider_name} returned HTTP {response.status_code}",
                    )

                try:
                    data = response.json()
                except ValueError as error:
                    raise ProviderError(
                        self.provider_name,
                        "invalid_response",
                        f"{self.provider_name} returned invalid JSON",
                    ) from error
                if not isinstance(data, dict):
                    raise ProviderError(
                        self.provider_name,
                        "invalid_response",
                        f"{self.provider_name} returned a non-object JSON response",
                    )
                return data

        raise AssertionError("Provider request loop must return or raise")

    async def _wait(self, attempt: int) -> None:
        delay = self.settings.retry_delay_seconds * (2**attempt)
        if delay > 0:
            await asyncio.sleep(delay)
