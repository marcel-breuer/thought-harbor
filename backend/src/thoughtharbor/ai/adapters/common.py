"""Validation helpers shared by provider adapters."""

from typing import Any

from pydantic import BaseModel, ValidationError

from thoughtharbor.ai.errors import StructuredOutputError
from thoughtharbor.ai.models import ModelMetadata


def response_text(data: dict[str, Any], provider: str) -> str:
    """Extract provider response text and reject missing content."""

    value = data.get("content")
    if not isinstance(value, str):
        raise StructuredOutputError(f"{provider} returned no text content")
    return value


def validate_structured(
    text: str, schema: type[BaseModel], metadata: ModelMetadata
) -> tuple[BaseModel, ModelMetadata]:
    """Validate JSON through Pydantic before an application can persist it."""

    try:
        return schema.model_validate_json(text), metadata
    except (ValidationError, ValueError) as error:
        raise StructuredOutputError(
            f"Provider returned invalid {schema.__name__} structured output"
        ) from error
