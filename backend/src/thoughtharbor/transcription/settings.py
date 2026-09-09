"""Environment-backed local transcription settings."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TranscriptionSettings:
    """CPU-safe defaults with explicit optional GPU configuration."""

    model_size: str
    device: str
    compute_type: str
    model_cache: str

    @classmethod
    def from_environment(cls) -> "TranscriptionSettings":
        return cls(
            model_size=os.environ.get("WHISPER_MODEL_SIZE", "small"),
            device=os.environ.get("WHISPER_DEVICE", "cpu"),
            compute_type=os.environ.get("WHISPER_COMPUTE_TYPE", "int8"),
            model_cache=os.environ.get("WHISPER_MODEL_CACHE", ".data/models/whisper"),
        )
