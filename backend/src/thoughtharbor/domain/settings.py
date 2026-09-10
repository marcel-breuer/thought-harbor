"""Safe, non-secret runtime configuration read model for the settings surface."""

import os
from dataclasses import dataclass

from thoughtharbor.ai.settings import AISettings
from thoughtharbor.diarization.settings import DiarizationSettings
from thoughtharbor.transcription.settings import TranscriptionSettings


@dataclass(frozen=True, slots=True)
class RuntimeSettingsView:
    chat_provider: str
    chat_model: str
    extraction_provider: str
    extraction_model: str
    embeddings_provider: str
    embeddings_model: str
    transcription_model: str
    transcription_device: str
    transcription_compute_type: str
    diarization_enabled: bool
    diarization_provider: str
    diarization_model: str
    max_upload_bytes: int
    external_provider_enabled: bool


class RuntimeSettingsService:
    """Resolve environment settings into a browser-safe, non-secret snapshot."""

    def get(self) -> RuntimeSettingsView:
        ai = AISettings.from_environment()
        transcription = TranscriptionSettings.from_environment()
        diarization = DiarizationSettings.from_environment()
        capabilities = (ai.chat, ai.extraction, ai.embeddings)
        return RuntimeSettingsView(
            chat_provider=ai.chat.provider,
            chat_model=ai.chat.model,
            extraction_provider=ai.extraction.provider,
            extraction_model=ai.extraction.model,
            embeddings_provider=ai.embeddings.provider,
            embeddings_model=ai.embeddings.model,
            transcription_model=transcription.model_size,
            transcription_device=transcription.device,
            transcription_compute_type=transcription.compute_type,
            diarization_enabled=diarization.enabled,
            diarization_provider=diarization.provider,
            diarization_model=diarization.model,
            max_upload_bytes=int(os.environ.get("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024))),
            external_provider_enabled=any(item.provider != "ollama" for item in capabilities),
        )
