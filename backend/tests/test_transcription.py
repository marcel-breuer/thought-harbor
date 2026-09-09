"""Deterministic tests for the local transcription adapter boundary."""

import sys
import types
from pathlib import Path

import pytest

from thoughtharbor.transcription.service import FasterWhisperTranscriber, TranscriptionError
from thoughtharbor.transcription.settings import TranscriptionSettings


def test_transcription_settings_use_cpu_safe_defaults(monkeypatch) -> None:
    for name in (
        "WHISPER_MODEL_SIZE",
        "WHISPER_DEVICE",
        "WHISPER_COMPUTE_TYPE",
        "WHISPER_MODEL_CACHE",
    ):
        monkeypatch.delenv(name, raising=False)

    assert TranscriptionSettings.from_environment() == TranscriptionSettings(
        model_size="small",
        device="cpu",
        compute_type="int8",
        model_cache=".data/models/whisper",
    )


def test_transcription_settings_allow_explicit_gpu_configuration(monkeypatch) -> None:
    monkeypatch.setenv("WHISPER_MODEL_SIZE", "medium")
    monkeypatch.setenv("WHISPER_DEVICE", "cuda")
    monkeypatch.setenv("WHISPER_COMPUTE_TYPE", "float16")
    monkeypatch.setenv("WHISPER_MODEL_CACHE", "/data/models/whisper")

    settings = TranscriptionSettings.from_environment()

    assert settings == TranscriptionSettings(
        model_size="medium",
        device="cuda",
        compute_type="float16",
        model_cache="/data/models/whisper",
    )


def test_faster_whisper_adapter_normalizes_timestamped_segments(
    monkeypatch, tmp_path: Path
) -> None:
    class FakeSegment:
        def __init__(self, start: float, end: float, text: str) -> None:
            self.start = start
            self.end = end
            self.text = text

    class FakeInfo:
        language = "de"

    class FakeModel:
        def __init__(self, *args, **kwargs) -> None:
            self.args = args
            self.kwargs = kwargs

        def transcribe(self, path: str, *, vad_filter: bool):
            assert path.endswith("sample.wav")
            assert vad_filter is True
            return iter(
                [
                    FakeSegment(-0.1, 1.234, "  Hallo Welt  "),
                    FakeSegment(1.5, 2.0, "   "),
                ]
            ), FakeInfo()

    monkeypatch.setitem(
        sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel)
    )
    settings = TranscriptionSettings("tiny", "cpu", "int8", str(tmp_path / "models"))
    result = FasterWhisperTranscriber(settings).transcribe(tmp_path / "sample.wav")

    assert result.language == "de"
    assert result.provider == "faster-whisper"
    assert result.model == "tiny"
    assert [(segment.start_ms, segment.end_ms, segment.text) for segment in result.segments] == [
        (0, 1234, "Hallo Welt")
    ]


def test_faster_whisper_adapter_reports_silent_audio(monkeypatch, tmp_path: Path) -> None:
    class FakeModel:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def transcribe(self, path: str, *, vad_filter: bool):
            return iter(()), object()

    monkeypatch.setitem(
        sys.modules, "faster_whisper", types.SimpleNamespace(WhisperModel=FakeModel)
    )
    transcriber = FasterWhisperTranscriber(
        TranscriptionSettings("tiny", "cpu", "int8", str(tmp_path / "models"))
    )

    with pytest.raises(TranscriptionError, match="no detectable speech"):
        transcriber.transcribe(tmp_path / "silent.wav")
