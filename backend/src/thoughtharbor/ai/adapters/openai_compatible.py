"""Adapter for OpenAI-compatible chat and embedding endpoints."""

from typing import Any

import httpx
from pydantic import BaseModel

from thoughtharbor.ai.adapters.common import validate_structured
from thoughtharbor.ai.adapters.http import HTTPProvider
from thoughtharbor.ai.errors import ProviderError, StructuredOutputError
from thoughtharbor.ai.models import (
    Capability,
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ExtractionRequest,
    ExtractionResult,
    ModelMetadata,
    message_payload,
)
from thoughtharbor.ai.settings import CapabilitySettings


class OpenAICompatibleProvider(HTTPProvider):
    """Call an explicitly configured OpenAI-compatible endpoint."""

    capabilities: tuple[Capability, ...] = (
        "chat",
        "structured_extraction",
        "embeddings",
    )

    def __init__(
        self,
        settings: CapabilitySettings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        super().__init__(settings, provider_name="openai_compatible", transport=transport)

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
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": message_payload(request.messages),
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        data = await self.post("/chat/completions", payload)
        text = _completion_text(data)
        return ChatResult(text=text, metadata=await self.metadata())

    async def extract(
        self, request: ExtractionRequest, schema: type[BaseModel]
    ) -> ExtractionResult[Any]:
        metadata = await self.metadata()
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": message_payload(request.messages),
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.schema_name,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens

        for attempt in range(self.settings.structured_retries + 1):
            data = await self.post("/chat/completions", payload)
            try:
                value, _ = validate_structured(_completion_text(data), schema, metadata)
                return ExtractionResult(value=value, metadata=metadata)
            except StructuredOutputError as error:
                if attempt == self.settings.structured_retries:
                    raise error
        raise AssertionError("Structured extraction loop must return or raise")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        data = await self.post(
            "/embeddings", {"model": self.settings.model, "input": request.texts}
        )
        raw_items = data.get("data")
        if not isinstance(raw_items, list) or len(raw_items) != len(request.texts):
            raise ProviderError(
                "openai_compatible", "invalid_response", "Provider returned invalid embeddings"
            )
        try:
            items = sorted(raw_items, key=lambda item: int(item["index"]))
            vectors = tuple(tuple(float(item) for item in vector["embedding"]) for vector in items)
        except (KeyError, TypeError, ValueError) as error:
            raise ProviderError(
                "openai_compatible", "invalid_response", "Provider returned malformed vectors"
            ) from error
        return EmbeddingResult(vectors=vectors, metadata=await self.metadata())


def _completion_text(data: dict[str, Any]) -> str:
    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as error:
        raise ProviderError(
            "openai_compatible", "invalid_response", "Provider returned no completion content"
        ) from error
    if not isinstance(text, str):
        raise ProviderError(
            "openai_compatible", "invalid_response", "Provider returned non-text completion"
        )
    return text
