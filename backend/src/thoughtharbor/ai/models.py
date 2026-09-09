"""Provider-neutral AI request, response, and metadata models."""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TypeVar

Capability = Literal["chat", "structured_extraction", "embeddings"]
MessageRole = Literal["system", "user", "assistant"]
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class ChatMessage:
    """One provider-neutral chat message."""

    role: MessageRole
    content: str


@dataclass(frozen=True, slots=True)
class ChatRequest:
    """Input for text generation."""

    messages: tuple[ChatMessage, ...]
    temperature: float | None = None
    max_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class ExtractionRequest:
    """Input for schema-constrained extraction."""

    messages: tuple[ChatMessage, ...]
    schema_name: str = "extraction"
    temperature: float | None = 0.0
    max_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class EmbeddingRequest:
    """Input for one or more embedding texts."""

    texts: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ModelMetadata:
    """Non-secret provider/model information attached to every result."""

    provider: str
    model: str
    model_version: str | None
    capabilities: tuple[Capability, ...]
    context_window: int | None
    max_output_tokens: int | None
    configuration_fingerprint: str

    def as_dict(self) -> dict[str, object]:
        """Return safe metadata suitable for ``ArtifactGeneration.metadata``."""

        return {
            "provider": self.provider,
            "model": self.model,
            "model_version": self.model_version,
            "capabilities": list(self.capabilities),
            "context_window": self.context_window,
            "max_output_tokens": self.max_output_tokens,
            "configuration_fingerprint": self.configuration_fingerprint,
        }


@dataclass(frozen=True, slots=True)
class ChatResult:
    """Generated text and the metadata needed to reproduce its origin."""

    text: str
    metadata: ModelMetadata


@dataclass(frozen=True, slots=True)
class ExtractionResult[T]:
    """Validated structured data and its generation metadata."""

    value: T
    metadata: ModelMetadata


@dataclass(frozen=True, slots=True)
class EmbeddingResult:
    """Embedding vectors and the metadata needed to identify the model."""

    vectors: tuple[tuple[float, ...], ...]
    metadata: ModelMetadata


def message_payload(messages: tuple[ChatMessage, ...]) -> list[Mapping[str, str]]:
    """Convert messages to the common JSON shape without exposing domain objects."""

    return [{"role": message.role, "content": message.content} for message in messages]
