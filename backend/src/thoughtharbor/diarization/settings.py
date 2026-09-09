"""Environment-backed local speaker-diarization settings."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DiarizationSettings:
    """Optional local diarization configuration."""

    enabled: bool
    provider: str
    model: str
    device: str
    model_cache: str
    huggingface_token: str | None

    @classmethod
    def from_environment(cls) -> "DiarizationSettings":
        """Load explicit opt-in settings without logging secret values."""

        return cls(
            enabled=os.environ.get("DIARIZATION_ENABLED", "false").casefold()
            in {"1", "true", "yes", "on"},
            provider=os.environ.get("DIARIZATION_PROVIDER", "pyannote"),
            model=os.environ.get("DIARIZATION_MODEL", "pyannote/speaker-diarization-community-1"),
            device=os.environ.get("DIARIZATION_DEVICE", "cpu"),
            model_cache=os.environ.get("DIARIZATION_MODEL_CACHE", ".data/models/diarization"),
            huggingface_token=os.environ.get("HUGGINGFACE_TOKEN") or None,
        )
