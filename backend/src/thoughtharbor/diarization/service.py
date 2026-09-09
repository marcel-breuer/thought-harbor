"""Provider-neutral local diarization and transcript speaker mapping."""

import tempfile
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from thoughtharbor.diarization.settings import DiarizationSettings
from thoughtharbor.domain.models import Meeting, SourceFile, Speaker, Transcript, TranscriptSegment
from thoughtharbor.storage.service import StorageService
from thoughtharbor.transcription.service import FFmpegAudioPreprocessor, TranscriptionError


class DiarizationError(Exception):
    """Raised when a configured local diarization adapter cannot run."""


@dataclass(frozen=True, slots=True)
class DiarizationInterval:
    """One speaker interval emitted by a diarization provider."""

    start_ms: int
    end_ms: int
    speaker_label: str
    confidence: float | None = None


@dataclass(frozen=True, slots=True)
class DiarizationResult:
    """Provider-neutral diarization output and quality metadata."""

    intervals: tuple[DiarizationInterval, ...]
    provider: str
    model: str
    model_version: str | None
    quality: dict[str, Any]


class SpeakerDiarizer(Protocol):
    """Replaceable local diarization port."""

    def diarize(self, audio_path: Path) -> DiarizationResult: ...


@dataclass(frozen=True, slots=True)
class SegmentSpan:
    """Timestamp span used by the pure mapping function."""

    segment_id: int
    start_ms: int
    end_ms: int


@dataclass(frozen=True, slots=True)
class SpeakerAssignment:
    """Anonymous label and optional confidence assigned to one segment."""

    label: str
    confidence: float | None


def map_intervals_to_segments(
    segments: Iterable[SegmentSpan], intervals: Iterable[DiarizationInterval]
) -> dict[int, SpeakerAssignment]:
    """Assign each transcript segment to the interval with greatest overlap."""

    interval_list = [interval for interval in intervals if interval.end_ms > interval.start_ms]
    assignments: dict[int, SpeakerAssignment] = {}
    for segment in segments:
        overlaps = [
            (
                min(segment.end_ms, interval.end_ms) - max(segment.start_ms, interval.start_ms),
                interval,
            )
            for interval in interval_list
        ]
        overlapping = [(overlap, interval) for overlap, interval in overlaps if overlap > 0]
        if not overlapping:
            continue
        _, interval = max(overlapping, key=lambda item: (item[0], -(interval_list.index(item[1]))))
        assignments[segment.segment_id] = SpeakerAssignment(
            label=interval.speaker_label,
            confidence=interval.confidence,
        )
    return assignments


class PyannoteDiarizer:
    """Lazy local adapter for the pyannote community pipeline."""

    def __init__(self, settings: DiarizationSettings) -> None:
        self.settings = settings
        self._pipeline: Any = None

    def diarize(self, audio_path: Path) -> DiarizationResult:
        token = self.settings.huggingface_token
        try:
            from pyannote.audio import Pipeline  # type: ignore[import-not-found]
        except ImportError as error:
            raise DiarizationError("pyannote.audio is not installed") from error
        try:
            if self._pipeline is None:
                arguments: dict[str, Any] = {"cache_dir": self.settings.model_cache}
                if token:
                    arguments["token"] = token
                self._pipeline = Pipeline.from_pretrained(
                    self.settings.model,
                    **arguments,
                )
                import torch  # type: ignore[import-not-found]

                self._pipeline.to(torch.device(self.settings.device))
            output = self._pipeline(str(audio_path))
            diarization = getattr(output, "exclusive_speaker_diarization", None) or getattr(
                output, "speaker_diarization", output
            )
            intervals = tuple(
                DiarizationInterval(
                    start_ms=max(0, round(float(turn.start) * 1000)),
                    end_ms=max(0, round(float(turn.end) * 1000)),
                    speaker_label=str(label),
                )
                for turn, _, label in diarization.itertracks(yield_label=True)
            )
        except Exception as error:
            raise DiarizationError("pyannote.audio could not diarize the audio") from error
        if not intervals:
            raise DiarizationError("The diarization model returned no speaker intervals")
        return DiarizationResult(
            intervals=intervals,
            provider="pyannote",
            model=self.settings.model,
            model_version=None,
            quality={"interval_count": len(intervals)},
        )


class DiarizationService:
    """Apply optional local diarization without invalidating a transcript."""

    def __init__(
        self,
        session: Session,
        storage: StorageService,
        *,
        diarizer: SpeakerDiarizer | None = None,
        preprocessor: FFmpegAudioPreprocessor | None = None,
        settings: DiarizationSettings | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.settings = settings or DiarizationSettings.from_environment()
        self.diarizer = diarizer
        self.preprocessor = preprocessor or FFmpegAudioPreprocessor()

    def process(self, meeting_id: int) -> bool:
        """Map local diarization intervals onto an existing transcript."""

        meeting = self.session.scalar(select(Meeting).where(Meeting.id == meeting_id))
        if meeting is None or meeting.source_file_id is None:
            return False
        transcript = self.session.scalar(
            select(Transcript).where(Transcript.meeting_id == meeting.id)
        )
        source = self.session.scalar(
            select(SourceFile).where(SourceFile.id == meeting.source_file_id)
        )
        if transcript is None or source is None:
            return False
        if not self.settings.enabled:
            self._record_metadata(meeting, source, {"status": "skipped", "reason": "disabled"})
            self.session.commit()
            return False
        try:
            with (
                self.storage.open_read(source.storage_key) as raw,
                tempfile.NamedTemporaryFile(suffix=".wav") as normalized,
            ):
                self.preprocessor.normalize(raw, Path(normalized.name))
                diarizer = self.diarizer or self._default_diarizer()
                result = diarizer.diarize(Path(normalized.name))
            self._persist_assignments(meeting, source, transcript, result)
        except (DiarizationError, OSError, TranscriptionError) as error:
            self._record_metadata(
                meeting,
                source,
                {"status": "unavailable", "error": str(error)},
            )
            self.session.commit()
            return False
        self.session.commit()
        return True

    def _persist_assignments(
        self,
        meeting: Meeting,
        source: SourceFile,
        transcript: Transcript,
        result: DiarizationResult,
    ) -> None:
        segments = list(
            self.session.scalars(
                select(TranscriptSegment)
                .where(TranscriptSegment.transcript_id == transcript.id)
                .order_by(TranscriptSegment.sequence)
            )
        )
        assignments = map_intervals_to_segments(
            (SegmentSpan(segment.id, segment.start_ms, segment.end_ms) for segment in segments),
            result.intervals,
        )
        previous_map = self._raw_label_map(meeting)
        labels: dict[str, str] = {
            raw_label: label
            for raw_label, label in previous_map.items()
            if any(assignment.label == raw_label for assignment in assignments.values())
        }
        previous_numbers = {
            int(label.removeprefix("Speaker "))
            for label in previous_map.values()
            if label.startswith("Speaker ") and label.removeprefix("Speaker ").isdigit()
        }
        next_label = max(previous_numbers, default=0) + 1
        for assignment in assignments.values():
            if assignment.label not in labels:
                labels[assignment.label] = f"Speaker {next_label}"
                next_label += 1
        speakers: dict[str, Speaker] = {}
        for label in labels.values():
            speaker = self.session.scalar(
                select(Speaker).where(Speaker.meeting_id == meeting.id, Speaker.label == label)
            )
            if speaker is None:
                speaker = Speaker(owner_id=meeting.owner_id, meeting_id=meeting.id, label=label)
                self.session.add(speaker)
                self.session.flush()
            speakers[label] = speaker
        confidence = {
            labels[assignment.label]: assignment.confidence
            for assignment in assignments.values()
            if assignment.confidence is not None
        }
        for segment in segments:
            segment_assignment = assignments.get(segment.id)
            if segment_assignment is not None:
                segment.speaker_id = speakers[labels[segment_assignment.label]].id
        self._record_metadata(
            meeting,
            source,
            {
                "status": "succeeded",
                "provider": result.provider,
                "model": result.model,
                "model_version": result.model_version,
                "speaker_count": len(speakers),
                "assigned_segment_count": len(assignments),
                "raw_label_map": labels,
                "quality": {**result.quality, "speaker_confidence": confidence},
            },
        )

    @staticmethod
    def _record_metadata(meeting: Meeting, source: SourceFile, diarization: dict[str, Any]) -> None:
        meeting.metadata_json = {**meeting.metadata_json, "diarization": diarization}
        source.metadata_json = {**source.metadata_json, "diarization": diarization}

    def _default_diarizer(self) -> SpeakerDiarizer:
        if self.settings.provider != "pyannote":
            raise DiarizationError(f"Unsupported diarization provider: {self.settings.provider}")
        return PyannoteDiarizer(self.settings)

    @staticmethod
    def _raw_label_map(meeting: Meeting) -> dict[str, str]:
        metadata = meeting.metadata_json.get("diarization", {})
        raw_label_map = metadata.get("raw_label_map", {}) if isinstance(metadata, dict) else {}
        return (
            {str(raw): str(label) for raw, label in raw_label_map.items()}
            if isinstance(raw_label_map, dict)
            else {}
        )
