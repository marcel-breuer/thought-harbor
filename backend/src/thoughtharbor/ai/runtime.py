"""Capability routing and request policy for the shared AI application layer."""

import math
from dataclasses import replace
from typing import cast

from pydantic import BaseModel

from thoughtharbor.ai.adapters.openai_compatible import OpenRouterProvider
from thoughtharbor.ai.errors import (
    CapabilityNotSupportedError,
    ContextWindowExceededError,
    ProviderConfigurationError,
    ProviderError,
)
from thoughtharbor.ai.models import (
    Capability,
    ChatMessage,
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ExtractionRequest,
    ExtractionResult,
)
from thoughtharbor.ai.protocols import (
    ChatGenerationPort,
    EmbeddingPort,
    StructuredExtractionPort,
    ensure_texts,
)
from thoughtharbor.ai.settings import AISettings, CapabilitySettings


class AIRuntime:
    """Route each capability to an independently configured provider port."""

    def __init__(
        self,
        chat: ChatGenerationPort,
        extraction: StructuredExtractionPort,
        embeddings: EmbeddingPort,
    ) -> None:
        self.chat_provider = chat
        self.extraction_provider = extraction
        self.embedding_provider = embeddings
        self._settings: AISettings | None = None

    @classmethod
    def from_environment(cls) -> "AIRuntime":
        """Build the runtime used by API, worker, and MCP processes."""

        return cls.from_settings(AISettings.from_environment())

    @classmethod
    def from_settings(cls, settings: AISettings) -> "AIRuntime":
        """Build one provider adapter per capability configuration."""

        runtime = cls(
            chat=cast(ChatGenerationPort, _provider(settings.chat)),
            extraction=cast(StructuredExtractionPort, _provider(settings.extraction)),
            embeddings=cast(EmbeddingPort, _provider(settings.embeddings)),
        )
        runtime._settings = settings
        return runtime

    def with_generation_model(self, model: str | None) -> "AIRuntime":
        """Create an isolated runtime view with a user-selected generation model."""

        if not model or self._settings is None:
            return self
        settings = replace(
            self._settings,
            chat=replace(self._settings.chat, model=model),
            extraction=replace(self._settings.extraction, model=model),
        )
        return self.from_settings(settings)

    async def chat(self, request: ChatRequest, *, model_id: str | None = None) -> ChatResult:
        """Generate text after capability and context checks."""

        if model_id and self._settings is not None:
            selected = self.with_generation_model(model_id)
            try:
                return await selected.chat(request)
            except ProviderError as error:
                if error.code != "model_not_found":
                    raise
                return await self.chat(request)

        metadata = await self.chat_provider.metadata()
        _check_request("chat", request.messages, request.max_tokens, metadata, self.chat_provider)
        return await self.chat_provider.chat(request)

    async def extract(
        self,
        request: ExtractionRequest,
        schema: type[BaseModel],
        *,
        model_id: str | None = None,
    ) -> ExtractionResult[BaseModel]:
        """Extract a Pydantic model; invalid results never leave the provider port."""

        if model_id and self._settings is not None:
            selected = self.with_generation_model(model_id)
            try:
                return await selected.extract(request, schema)
            except ProviderError as error:
                if error.code != "model_not_found":
                    raise
                return await self.extract(request, schema)

        metadata = await self.extraction_provider.metadata()
        _check_request(
            "structured_extraction",
            request.messages,
            request.max_tokens,
            metadata,
            self.extraction_provider,
        )
        return await self.extraction_provider.extract(request, schema)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed texts through the independently configured embeddings provider."""

        ensure_texts(request.texts)
        if not self.embedding_provider.supports("embeddings"):
            raise CapabilityNotSupportedError("configured provider", "embeddings")
        return await self.embedding_provider.embed(request)

    async def close(self) -> None:
        """Keep a lifecycle hook for future pooled transports."""


def _provider(
    settings: CapabilitySettings,
) -> OpenRouterProvider:
    if settings.provider == "openrouter":
        return OpenRouterProvider(settings)
    raise ProviderConfigurationError(f"Unknown AI provider: {settings.provider!r}")


def _check_request(
    capability: Capability,
    messages: tuple[ChatMessage, ...],
    requested_output_tokens: int | None,
    metadata: object,
    provider: ChatGenerationPort | StructuredExtractionPort,
) -> None:
    if not provider.supports(capability):
        provider_name = getattr(metadata, "provider", "configured provider")
        raise CapabilityNotSupportedError(provider_name, capability)

    context_window = getattr(metadata, "context_window", None)
    configured_output = getattr(metadata, "max_output_tokens", None)
    output_tokens = requested_output_tokens or configured_output or 0
    if configured_output is not None and output_tokens > configured_output:
        raise ContextWindowExceededError(
            f"Requested output token limit {output_tokens} exceeds configured limit "
            f"{configured_output} for {capability}"
        )
    if context_window is None:
        return
    input_tokens = sum(max(1, math.ceil(len(message.content) / 4)) for message in messages)
    if input_tokens + output_tokens > context_window:
        raise ContextWindowExceededError(
            f"{capability} request needs approximately {input_tokens + output_tokens} tokens, "
            f"but the configured context window is {context_window}"
        )
