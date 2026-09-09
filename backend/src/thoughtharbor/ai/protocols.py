"""Application-facing ports for AI capabilities."""

from collections.abc import Sequence
from typing import Protocol, TypeVar

from pydantic import BaseModel

from thoughtharbor.ai.models import (
    Capability,
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
    ExtractionRequest,
    ExtractionResult,
    ModelMetadata,
)

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class ModelMetadataPort(Protocol):
    """Port for safe provider/model metadata."""

    async def metadata(self) -> ModelMetadata:
        """Return metadata without returning credentials or prompt content."""


class ChatGenerationPort(ModelMetadataPort, Protocol):
    """Port for provider-neutral text generation."""

    def supports(self, capability: Capability) -> bool:
        """Return whether this configured provider supports a capability."""

    async def chat(self, request: ChatRequest) -> ChatResult:
        """Generate text."""


class StructuredExtractionPort(ModelMetadataPort, Protocol):
    """Port for Pydantic-validated structured extraction."""

    def supports(self, capability: Capability) -> bool:
        """Return whether structured extraction is available."""

    async def extract(
        self, request: ExtractionRequest, schema: type[SchemaT]
    ) -> ExtractionResult[SchemaT]:
        """Generate and validate one schema instance."""


class EmbeddingPort(ModelMetadataPort, Protocol):
    """Port for text embeddings."""

    def supports(self, capability: Capability) -> bool:
        """Return whether embeddings are available."""

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed one or more texts."""


class AIRuntimePorts(Protocol):
    """The complete set of ports consumed by application services."""

    chat: ChatGenerationPort
    extraction: StructuredExtractionPort
    embeddings: EmbeddingPort

    async def close(self) -> None:
        """Release provider resources."""


def ensure_texts(texts: Sequence[str]) -> tuple[str, ...]:
    """Normalize embedding input and reject an empty batch early."""

    normalized = tuple(texts)
    if not normalized:
        raise ValueError("At least one text is required for embeddings")
    return normalized
