"""Adapter for Google's Gemini generateContent API."""

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


class GeminiProvider(HTTPProvider):
    """Use Gemini for chat and schema-validated extraction."""

    capabilities: tuple[Capability, ...] = ("chat", "structured_extraction")

    def __init__(
        self,
        settings: CapabilitySettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(settings, provider_name="gemini", transport=transport)

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
        data = await self._generate(request.messages, request.temperature, request.max_tokens)
        return ChatResult(text=_response_text(data), metadata=await self.metadata())

    async def extract(
        self, request: ExtractionRequest, schema: type[BaseModel]
    ) -> ExtractionResult[Any]:
        metadata = await self.metadata()
        for attempt in range(self.settings.structured_retries + 1):
            data = await self._generate(
                request.messages,
                request.temperature,
                request.max_tokens,
                schema=schema,
            )
            try:
                value, _ = validate_structured(_response_text(data), schema, metadata)
                return ExtractionResult(value=value, metadata=metadata)
            except StructuredOutputError as error:
                if attempt == self.settings.structured_retries:
                    raise error
        raise AssertionError("Structured extraction loop must return or raise")

    async def _generate(
        self,
        messages: tuple[ChatMessage, ...],
        temperature: float | None,
        max_tokens: int | None,
        *,
        schema: type[BaseModel] | None = None,
    ) -> dict[str, Any]:
        generation_config: dict[str, Any] = {"maxOutputTokens": max_tokens or 1024}
        if temperature is not None:
            generation_config["temperature"] = temperature
        if schema is not None:
            generation_config["responseMimeType"] = "application/json"
            generation_config["responseSchema"] = schema.model_json_schema()
        data = await self.post(
            f"/models/{self.settings.model}:generateContent",
            _content_payload(messages, generation_config),
            extra_headers=_headers(self.settings.api_key),
            include_bearer=False,
        )
        return data


def _headers(api_key: str | None) -> dict[str, str]:
    return {"x-goog-api-key": api_key} if api_key else {}


def _content_payload(
    messages: tuple[ChatMessage, ...], generation_config: dict[str, Any]
) -> dict[str, Any]:
    system = [message.content for message in messages if message.role == "system"]
    payload: dict[str, Any] = {
        "contents": [
            {
                "role": "model" if message.role == "assistant" else "user",
                "parts": [{"text": message.content}],
            }
            for message in messages
            if message.role != "system"
        ],
        "generationConfig": generation_config,
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": "\n\n".join(system)}]}
    return payload


def _response_text(data: dict[str, Any]) -> str:
    try:
        parts = data["candidates"][0]["content"]["parts"]
    except (KeyError, IndexError, TypeError) as error:
        raise ProviderError("gemini", "invalid_response", "Gemini returned no content") from error
    text = "".join(part.get("text", "") for part in parts if isinstance(part, dict))
    if not text:
        raise ProviderError("gemini", "invalid_response", "Gemini returned no text content")
    return text
