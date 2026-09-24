"""Environment-backed, per-capability AI configuration."""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from typing import Final

DEFAULT_OPENROUTER_URL: Final = "https://openrouter.ai/api/v1"
DEFAULT_CHAT_MODEL: Final = "openai/gpt-4o-mini"
DEFAULT_EMBEDDING_MODEL: Final = "openai/text-embedding-3-small"
EMBEDDING_DIMENSIONS: Final = 768


@dataclass(frozen=True, slots=True)
class CapabilitySettings:
    """Configuration for one AI capability; secrets are never fingerprinted."""

    provider: str
    model: str
    base_url: str
    api_key: str | None
    timeout_seconds: float
    max_retries: int
    retry_delay_seconds: float
    context_window: int | None
    max_output_tokens: int | None
    structured_retries: int
    model_version: str | None = None

    def fingerprint(self) -> str:
        """Create a stable non-secret identity for this runtime configuration."""

        values = asdict(self)
        values.pop("api_key", None)
        encoded = json.dumps(values, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class AISettings:
    """All capability-specific runtime settings."""

    chat: CapabilitySettings
    extraction: CapabilitySettings
    embeddings: CapabilitySettings

    @classmethod
    def from_environment(cls) -> "AISettings":
        """Read deployment-wide OpenRouter settings."""

        base_url = os.environ.get("OPENROUTER_BASE_URL", DEFAULT_OPENROUTER_URL).rstrip("/")
        api_key = os.environ.get("OPENROUTER_API_KEY") or None
        default_model = os.environ.get("OPENROUTER_DEFAULT_MODEL", DEFAULT_CHAT_MODEL).strip()
        embedding_model = os.environ.get(
            "OPENROUTER_EMBEDDINGS_MODEL", DEFAULT_EMBEDDING_MODEL
        ).strip()
        return cls(
            chat=_capability_from_environment("CHAT", default_model, base_url, api_key),
            extraction=_capability_from_environment("EXTRACTION", default_model, base_url, api_key),
            embeddings=_capability_from_environment(
                "EMBEDDINGS", embedding_model, base_url, api_key
            ),
        )


def _capability_from_environment(
    name: str, default_model: str, base_url: str, api_key: str | None
) -> CapabilitySettings:
    prefix = f"AI_{name}_"
    return CapabilitySettings(
        provider="openrouter",
        model=default_model,
        base_url=base_url,
        api_key=api_key,
        timeout_seconds=float(os.environ.get(f"{prefix}TIMEOUT_SECONDS", "60")),
        max_retries=int(os.environ.get(f"{prefix}MAX_RETRIES", "2")),
        retry_delay_seconds=float(os.environ.get(f"{prefix}RETRY_DELAY_SECONDS", "0.5")),
        context_window=_optional_int(os.environ.get(f"{prefix}CONTEXT_WINDOW")),
        max_output_tokens=_optional_int(os.environ.get(f"{prefix}MAX_OUTPUT_TOKENS")),
        structured_retries=int(os.environ.get(f"{prefix}STRUCTURED_RETRIES", "1")),
        model_version=os.environ.get(f"{prefix}MODEL_VERSION") or None,
    )


def _optional_int(value: str | None) -> int | None:
    return int(value) if value else None
