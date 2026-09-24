"""Safe, generation-capable model catalogue for the OpenRouter profile selector."""

from dataclasses import dataclass
from typing import Any

import httpx

from thoughtharbor.ai.errors import ProviderError
from thoughtharbor.ai.settings import AISettings


@dataclass(frozen=True, slots=True)
class AvailableModel:
    """Public model details needed to make a profile choice."""

    id: str
    name: str
    context_length: int | None
    prompt_price: float | None
    completion_price: float | None


class OpenRouterModelCatalog:
    """Fetch the OpenRouter models that support chat and JSON-schema output."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.settings = AISettings.from_environment().chat
        self._transport = transport

    async def generation_models(self) -> tuple[AvailableModel, ...]:
        """Return model IDs eligible for both chat and structured extraction."""

        if not self.settings.api_key:
            raise ProviderError(
                "openrouter", "configuration", "OPENROUTER_API_KEY is not configured"
            )
        try:
            async with httpx.AsyncClient(
                base_url=self.settings.base_url,
                headers={"Authorization": f"Bearer {self.settings.api_key}"},
                timeout=self.settings.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = await client.get(
                    "/models",
                    params={
                        "output_modalities": "text",
                        "supported_parameters": "response_format",
                    },
                )
        except httpx.TimeoutException as error:
            raise ProviderError(
                "openrouter", "timeout", "OpenRouter model list timed out"
            ) from error
        except httpx.NetworkError as error:
            raise ProviderError(
                "openrouter", "unavailable", "OpenRouter could not be reached"
            ) from error

        if response.status_code in {401, 403}:
            raise ProviderError(
                "openrouter", "authentication", "OpenRouter rejected the configured credentials"
            )
        if response.status_code == 429:
            raise ProviderError(
                "openrouter", "rate_limited", "OpenRouter model list is rate limited"
            )
        if response.status_code >= 500:
            raise ProviderError("openrouter", "unavailable", "OpenRouter model list is unavailable")
        if response.status_code >= 400:
            raise ProviderError(
                "openrouter", "request_failed", f"OpenRouter returned HTTP {response.status_code}"
            )
        try:
            data = response.json()
        except ValueError as error:
            raise ProviderError(
                "openrouter", "invalid_response", "OpenRouter returned invalid JSON"
            ) from error
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise ProviderError(
                "openrouter", "invalid_response", "OpenRouter returned an invalid model list"
            )
        return tuple(model for item in data["data"] if (model := _model(item)) is not None)


def _model(item: Any) -> AvailableModel | None:
    if not isinstance(item, dict):
        return None
    model_id = item.get("id")
    name = item.get("name")
    supported = item.get("supported_parameters")
    if not isinstance(model_id, str) or not model_id or not isinstance(name, str):
        return None
    if not isinstance(supported, list) or "response_format" not in supported:
        return None
    context_length = item.get("context_length")
    pricing = item.get("pricing")
    return AvailableModel(
        id=model_id,
        name=name,
        context_length=context_length if isinstance(context_length, int) else None,
        prompt_price=_price(pricing, "prompt"),
        completion_price=_price(pricing, "completion"),
    )


def _price(pricing: Any, key: str) -> float | None:
    if not isinstance(pricing, dict):
        return None
    try:
        return float(pricing[key])
    except (KeyError, TypeError, ValueError):
        return None
