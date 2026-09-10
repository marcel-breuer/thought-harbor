"""Adapter for Anthropic's Messages API."""

from typing import Any

import httpx
from pydantic import BaseModel

from thoughtharbor.ai.adapters.common import validate_structured
from thoughtharbor.ai.adapters.http import HTTPProvider
from thoughtharbor.ai.errors import ProviderError, StructuredOutputError
from thoughtharbor.ai.models import (
    Capability,
    ChatMessage,
    ChatRequest,
    ChatResult,
    ExtractionRequest,
    ExtractionResult,
    ModelMetadata,
)
from thoughtharbor.ai.settings import CapabilitySettings


class AnthropicProvider(HTTPProvider):
    """Use Anthropic for chat and schema-validated extraction."""

    capabilities: tuple[Capability, ...] = ("chat", "structured_extraction")

    def __init__(
        self,
        settings: CapabilitySettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(settings, provider_name="anthropic", transport=transport)

    def supports(self, capability: Capability) -> bool:
        return capability in self.capabilities

    async def metadata(self) -> ModelMetadata:
        return ModelMetadata(
            provider=self.provider_name,
            model=self.settings.model,
            model_version=self.settings.model_version,
            capabilities=self.capabilities,
            context_window=self.settings.context_window,
            max_output_tokens=self.settings.max_output_tokens,
            configuration_fingerprint=self.settings.fingerprint(),
        )

    async def chat(self, request: ChatRequest) -> ChatResult:
        data = await self.post(
            "/v1/messages",
            _message_payload(request.messages, self.settings.model, request.max_tokens),
            extra_headers=_headers(self.settings.api_key),
            include_bearer=False,
        )
        return ChatResult(text=_response_text(data), metadata=await self.metadata())

    async def extract(
        self, request: ExtractionRequest, schema: type[BaseModel]
    ) -> ExtractionResult[Any]:
        metadata = await self.metadata()
        messages = request.messages + (
            ChatMessage(
                "user",
                "Return only valid JSON matching this JSON Schema. "
                f"Schema: {schema.model_json_schema()}",
            ),
        )
        payload = _message_payload(messages, self.settings.model, request.max_tokens)
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        for attempt in range(self.settings.structured_retries + 1):
            data = await self.post(
                "/v1/messages",
                payload,
                extra_headers=_headers(self.settings.api_key),
                include_bearer=False,
            )
            try:
                value, _ = validate_structured(_response_text(data), schema, metadata)
                return ExtractionResult(value=value, metadata=metadata)
            except StructuredOutputError as error:
                if attempt == self.settings.structured_retries:
                    raise error
        raise AssertionError("Structured extraction loop must return or raise")


def _headers(api_key: str | None) -> dict[str, str]:
    if not api_key:
        return {"anthropic-version": "2023-06-01"}
    return {"x-api-key": api_key, "anthropic-version": "2023-06-01"}


def _message_payload(
    messages: tuple[ChatMessage, ...], model: str, max_tokens: int | None
) -> dict[str, Any]:
    system = [message.content for message in messages if message.role == "system"]
    payload: dict[str, Any] = {
        "model": model,
        "max_tokens": max_tokens or 1024,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in messages
            if message.role != "system"
        ],
    }
    if system:
        payload["system"] = "\n\n".join(system)
    return payload


def _response_text(data: dict[str, Any]) -> str:
    content = data.get("content")
    if not isinstance(content, list):
        raise ProviderError("anthropic", "invalid_response", "Anthropic returned no content")
    text = "".join(
        block.get("text", "")
        for block in content
        if isinstance(block, dict) and block.get("type") == "text"
    )
    if not text:
        raise ProviderError("anthropic", "invalid_response", "Anthropic returned no text content")
    return text
