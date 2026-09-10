"""Ollama's local HTTP API adapter."""

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


class OllamaProvider(HTTPProvider):
    """Use Ollama for chat, JSON-schema extraction, and embeddings."""

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
        super().__init__(settings, provider_name="ollama", transport=transport)

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
        options: dict[str, Any] = {}
        if request.temperature is not None:
            options["temperature"] = request.temperature
        if request.max_tokens is not None:
            options["num_predict"] = request.max_tokens
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": message_payload(request.messages),
            "stream": False,
        }
        if options:
            payload["options"] = options
        data = await self.post("/api/chat", payload)
        message = data.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ProviderError("ollama", "invalid_response", "Ollama returned no chat content")
        return ChatResult(text=message["content"], metadata=await self.metadata())

    async def extract(
        self, request: ExtractionRequest, schema: type[BaseModel]
    ) -> ExtractionResult[Any]:
        metadata = await self.metadata()
        payload: dict[str, Any] = {
            "model": self.settings.model,
            "messages": message_payload(request.messages),
            "stream": False,
            "format": schema.model_json_schema(),
        }
        if request.temperature is not None or request.max_tokens is not None:
            payload["options"] = {}
            if request.temperature is not None:
                payload["options"]["temperature"] = request.temperature
            if request.max_tokens is not None:
                payload["options"]["num_predict"] = request.max_tokens

        for attempt in range(self.settings.structured_retries + 1):
            data = await self.post("/api/chat", payload)
            message = data.get("message")
            text = message.get("content") if isinstance(message, dict) else None
            if not isinstance(text, str):
                error = StructuredOutputError("Ollama returned no structured content")
            else:
                try:
                    value, _ = validate_structured(text, schema, metadata)
                    return ExtractionResult(value=value, metadata=metadata)
                except StructuredOutputError as caught:
                    error = caught
            if attempt == self.settings.structured_retries:
                raise error
        raise AssertionError("Structured extraction loop must return or raise")

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        payload: dict[str, Any] = {"model": self.settings.model, "input": request.texts}
        if self.settings.model == "qwen3-embedding:0.6b":
            payload["dimensions"] = 768
        data = await self.post("/api/embed", payload)
        embeddings = data.get("embeddings")
        if not isinstance(embeddings, list) or len(embeddings) != len(request.texts):
            raise ProviderError("ollama", "invalid_response", "Ollama returned invalid embeddings")
        vectors = _vectors(embeddings)
        return EmbeddingResult(vectors=vectors, metadata=await self.metadata())


def _vectors(value: list[Any]) -> tuple[tuple[float, ...], ...]:
    vectors: list[tuple[float, ...]] = []
    for vector in value:
        if not isinstance(vector, list) or not all(
            isinstance(item, (int, float)) for item in vector
        ):
            raise ProviderError(
                "ollama", "invalid_response", "Provider returned a malformed vector"
            )
        vectors.append(tuple(float(item) for item in vector))
    return tuple(vectors)
