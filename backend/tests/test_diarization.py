"""Deterministic tests for diarization mapping and local configuration."""

from thoughtharbor.diarization.service import (
    DiarizationError,
    DiarizationInterval,
    DiarizationResult,
    SegmentSpan,
    map_intervals_to_segments,
)
from thoughtharbor.diarization.settings import DiarizationSettings


def test_diarization_settings_are_opt_in_and_cpu_first(monkeypatch) -> None:
    for name in (
        "DIARIZATION_ENABLED",
        "DIARIZATION_PROVIDER",
        "DIARIZATION_MODEL",
        "DIARIZATION_DEVICE",
        "DIARIZATION_MODEL_CACHE",
        "HUGGINGFACE_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)

    assert DiarizationSettings.from_environment() == DiarizationSettings(
        enabled=False,
        provider="pyannote",
        model="pyannote/speaker-diarization-community-1",
        device="cpu",
        model_cache=".data/models/diarization",
        huggingface_token=None,
    )


def test_mapping_assigns_greatest_overlap_and_leaves_gaps_unassigned() -> None:
    assignments = map_intervals_to_segments(
        [SegmentSpan(1, 0, 1000), SegmentSpan(2, 1000, 2000), SegmentSpan(3, 3000, 4000)],
        [
            DiarizationInterval(0, 700, "raw-a", 0.8),
            DiarizationInterval(700, 1600, "raw-b", 0.9),
            DiarizationInterval(2000, 2500, "raw-c"),
        ],
    )

    assert assignments[1].label == "raw-a"
    assert assignments[2].label == "raw-b"
    assert assignments[2].confidence == 0.9
    assert 3 not in assignments


def test_diarization_result_keeps_provider_quality_metadata() -> None:
    result = DiarizationResult(
        intervals=(DiarizationInterval(0, 100, "speaker"),),
        provider="pyannote",
        model="community-1",
        model_version="test",
        quality={"interval_count": 1},
    )

    assert result.quality == {"interval_count": 1}
    assert not issubclass(DiarizationError, RuntimeError)


def test_diarization_settings_allow_explicit_local_gpu(monkeypatch) -> None:
    monkeypatch.setenv("DIARIZATION_ENABLED", "true")
    monkeypatch.setenv("DIARIZATION_DEVICE", "cuda")
    monkeypatch.setenv("DIARIZATION_MODEL_CACHE", "/data/models/diarization")
    monkeypatch.setenv("HUGGINGFACE_TOKEN", "secret")

    settings = DiarizationSettings.from_environment()

    assert settings.enabled is True
    assert settings.device == "cuda"
    assert settings.model_cache == "/data/models/diarization"
    assert settings.huggingface_token == "secret"
