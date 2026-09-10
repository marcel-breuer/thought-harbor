"""Environment-backed, per-capability AI configuration."""

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from typing import Final

DEFAULT_OLLAMA_URL: Final = "http://localhost:11434"
DEFAULT_CHAT_MODEL: Final = "qwen3.8"
DEFAULT_EMBEDDING_MODEL: Final = "qwen3-embedding:0.6b"


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
        """Read settings while keeping Ollama the self-hosted default."""

        default_provider = os.environ.get("AI_DEFAULT_PROVIDER", "ollama").strip().lower()
        ollama_url = os.environ.get("OLLAMA_BASE_URL", DEFAULT_OLLAMA_URL).rstrip("/")
        return cls(
            chat=_capability_from_environment(
                "CHAT", default_provider, DEFAULT_CHAT_MODEL, ollama_url
            ),
            extraction=_capability_from_environment(
                "EXTRACTION", default_provider, DEFAULT_CHAT_MODEL, ollama_url
            ),
            embeddings=_capability_from_environment(
                "EMBEDDINGS", default_provider, DEFAULT_EMBEDDING_MODEL, ollama_url
            ),
        )


def _capability_from_environment(
    name: str, default_provider: str, default_model: str, ollama_url: str
) -> CapabilitySettings:
    prefix = f"AI_{name}_"
    provider = os.environ.get(f"{prefix}PROVIDER", default_provider).strip().lower()
    configured_url = os.environ.get(f"{prefix}BASE_URL", "").strip()
    default_url = ollama_url if provider == "ollama" else ""
    base_url = (configured_url or default_url).rstrip("/")
    model = os.environ.get(f"{prefix}MODEL", default_model).strip()
    api_key = os.environ.get(f"{prefix}API_KEY") or None
    return CapabilitySettings(
        provider=provider,
        model=model,
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
