"""Capability routing and request policy for the shared AI application layer."""

import math
from typing import cast

from pydantic import BaseModel

from thoughtharbor.ai.adapters.anthropic import AnthropicProvider
from thoughtharbor.ai.adapters.gemini import GeminiProvider
from thoughtharbor.ai.adapters.ollama import OllamaProvider
from thoughtharbor.ai.adapters.openai_compatible import OpenAICompatibleProvider
from thoughtharbor.ai.errors import (
    CapabilityNotSupportedError,
    ContextWindowExceededError,
    ProviderConfigurationError,
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

    @classmethod
    def from_environment(cls) -> "AIRuntime":
        """Build the runtime used by API, worker, and MCP processes."""

        return cls.from_settings(AISettings.from_environment())

    @classmethod
    def from_settings(cls, settings: AISettings) -> "AIRuntime":
        """Build one provider adapter per capability configuration."""

        return cls(
            chat=cast(ChatGenerationPort, _provider(settings.chat)),
            extraction=cast(StructuredExtractionPort, _provider(settings.extraction)),
            embeddings=cast(EmbeddingPort, _provider(settings.embeddings)),
        )

    async def chat(self, request: ChatRequest) -> ChatResult:
        """Generate text after capability and context checks."""

        metadata = await self.chat_provider.metadata()
        _check_request("chat", request.messages, request.max_tokens, metadata, self.chat_provider)
        return await self.chat_provider.chat(request)

    async def extract(
        self, request: ExtractionRequest, schema: type[BaseModel]
    ) -> ExtractionResult[BaseModel]:
        """Extract a Pydantic model; invalid results never leave the provider port."""

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
) -> OllamaProvider | OpenAICompatibleProvider | AnthropicProvider | GeminiProvider:
    if settings.provider == "ollama":
        return OllamaProvider(settings)
    if settings.provider == "openai":
        if not settings.base_url:
            raise ProviderConfigurationError("OpenAI provider requires a capability base URL")
        return OpenAICompatibleProvider(settings, provider_name="openai")
    if settings.provider == "openai_compatible":
        if not settings.base_url:
            raise ProviderConfigurationError(
                "OpenAI-compatible provider requires an explicit capability base URL"
            )
        return OpenAICompatibleProvider(settings)
    if settings.provider == "anthropic":
        if not settings.base_url:
            raise ProviderConfigurationError("Anthropic provider requires a capability base URL")
        return AnthropicProvider(settings)
    if settings.provider == "gemini":
        if not settings.base_url:
            raise ProviderConfigurationError("Gemini provider requires a capability base URL")
        return GeminiProvider(settings)
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
