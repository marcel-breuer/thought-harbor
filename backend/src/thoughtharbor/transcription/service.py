"""Local FFmpeg and faster-whisper transcription application services."""

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO, Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thoughtharbor.domain.models import (
    Meeting,
    ProcessingAttempt,
    ProcessingJob,
    SourceFile,
    Transcript,
    TranscriptSegment,
)
from thoughtharbor.storage.service import StorageService
from thoughtharbor.transcription.settings import TranscriptionSettings


class TranscriptionError(Exception):
    """Raised when local audio normalization or transcription fails."""


@dataclass(frozen=True, slots=True)
class TranscribedSegment:
    """One timestamped segment returned by a local transcriber."""

    start_ms: int
    end_ms: int
    text: str


@dataclass(frozen=True, slots=True)
class TranscriptionResult:
    """Provider-neutral transcription result."""

    language: str | None
    segments: tuple[TranscribedSegment, ...]
    provider: str
    model: str
    model_version: str | None


class Transcriber(Protocol):
    """Pluggable local transcription port."""

    def transcribe(self, audio_path: Path) -> TranscriptionResult: ...


class FFmpegAudioPreprocessor:
    """Normalize arbitrary supported audio to mono 16 kHz WAV."""

    def __init__(self, executable: str = "ffmpeg") -> None:
        self.executable = executable

    def normalize(self, source: BinaryIO, output_path: Path) -> None:
        """Copy source to a private temporary file and invoke FFmpeg safely."""

        with tempfile.NamedTemporaryFile(
            prefix="thoughtharbor-audio-", suffix=".input", delete=False
        ) as raw:
            input_path = Path(raw.name)
            shutil.copyfileobj(source, raw)
        try:
            command = [
                self.executable,
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(input_path),
                "-ac",
                "1",
                "-ar",
                "16000",
                "-f",
                "wav",
                "-y",
                str(output_path),
            ]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True)
            except FileNotFoundError as error:
                raise TranscriptionError("FFmpeg is not installed in the worker image") from error
            except subprocess.CalledProcessError as error:
                detail = error.stderr.strip() if error.stderr else "invalid or corrupt audio"
                raise TranscriptionError(f"FFmpeg could not decode the audio: {detail}") from error
        finally:
            input_path.unlink(missing_ok=True)


class FasterWhisperTranscriber:
    """Lazy-load faster-whisper so API imports never download model files."""

    def __init__(self, settings: TranscriptionSettings) -> None:
        self.settings = settings
        self._model: Any = None

    def transcribe(self, audio_path: Path) -> TranscriptionResult:
        try:
            from faster_whisper import WhisperModel  # type: ignore[import-untyped]
        except ImportError as error:
            raise TranscriptionError("faster-whisper is not installed") from error
        try:
            if self._model is None:
                self._model = WhisperModel(
                    self.settings.model_size,
                    device=self.settings.device,
                    compute_type=self.settings.compute_type,
                    download_root=self.settings.model_cache,
                )
            segments, info = self._model.transcribe(str(audio_path), vad_filter=True)
            normalized = tuple(
                TranscribedSegment(
                    start_ms=max(0, round(float(segment.start) * 1000)),
                    end_ms=max(0, round(float(segment.end) * 1000)),
                    text=str(segment.text).strip(),
                )
                for segment in segments
                if str(segment.text).strip()
            )
        except Exception as error:
            raise TranscriptionError("faster-whisper could not transcribe the audio") from error
        if not normalized:
            raise TranscriptionError("The audio contains no detectable speech")
        language = getattr(info, "language", None)
        return TranscriptionResult(
            language=language if isinstance(language, str) else None,
            segments=normalized,
            provider="faster-whisper",
            model=self.settings.model_size,
            model_version=None,
        )


class TranscriptionService:
    """Persist timestamped local transcripts without blocking FastAPI."""

    def __init__(
        self,
        session: Session,
        storage: StorageService,
        *,
        transcriber: Transcriber | None = None,
        preprocessor: FFmpegAudioPreprocessor | None = None,
        settings: TranscriptionSettings | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.settings = settings or TranscriptionSettings.from_environment()
        self.transcriber = transcriber or FasterWhisperTranscriber(self.settings)
        self.preprocessor = preprocessor or FFmpegAudioPreprocessor()

    def process(self, source_file_id: int) -> Transcript | None:
        """Transcribe one audio source idempotently and update its processing job."""

        source = self.session.scalar(
            select(SourceFile).where(
                SourceFile.id == source_file_id, SourceFile.deleted_at.is_(None)
            )
        )
        if source is None:
            return None
        existing = self.session.scalar(
            select(Transcript)
            .join(Meeting, Transcript.meeting_id == Meeting.id)
            .where(Meeting.source_file_id == source.id)
        )
        if existing is not None:
            return existing
        job = self.session.scalar(
            select(ProcessingJob)
            .where(
                ProcessingJob.subject_type == "source_file", ProcessingJob.subject_id == source.id
            )
            .order_by(ProcessingJob.id.desc())
        )
        if job is None:
            return None
        attempt = self._start_attempt(job)
        self._set_status(source, "transcribing", 0.0)
        job.metadata_json = {**job.metadata_json, "stage": "transcribing", "progress": 0.0}
        self.session.commit()
        try:
            with (
                self.storage.open_read(source.storage_key) as raw,
                tempfile.NamedTemporaryFile(suffix=".wav") as normalized,
            ):
                normalized_path = Path(normalized.name)
                self.preprocessor.normalize(raw, normalized_path)
                result = self.transcriber.transcribe(normalized_path)
            if not result.segments:
                raise TranscriptionError("The audio contains no timestamped speech segments")
            transcript = self._persist(source, result)
        except (OSError, TranscriptionError) as error:
            self._mark_failed(source, job, attempt, str(error))
            return None

        attempt.status = "succeeded"
        attempt.finished_at = datetime.now(UTC)
        job.status = "succeeded"
        job.metadata_json = {**job.metadata_json, "stage": "ready", "progress": 1.0}
        self._set_status(source, "ready", 1.0)
        self.session.commit()
        return transcript

    def _persist(self, source: SourceFile, result: TranscriptionResult) -> Transcript:
        title = source.original_name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        meeting = Meeting(
            owner_id=source.owner_id,
            source_file_id=source.id,
            title=title,
            metadata_json={
                "transcription_provider": result.provider,
                "transcription_model": result.model,
            },
        )
        self.session.add(meeting)
        self.session.flush()
        transcript = Transcript(
            owner_id=source.owner_id,
            meeting_id=meeting.id,
            language=result.language,
            provider=result.provider,
            model=result.model,
        )
        self.session.add(transcript)
        self.session.flush()
        for sequence, segment in enumerate(result.segments):
            self.session.add(
                TranscriptSegment(
                    transcript_id=transcript.id,
                    sequence=sequence,
                    text=segment.text,
                    start_ms=segment.start_ms,
                    end_ms=max(segment.start_ms, segment.end_ms),
                )
            )
        source.metadata_json = {
            **source.metadata_json,
            "transcription": {
                "provider": result.provider,
                "model": result.model,
                "model_version": result.model_version,
                "language": result.language,
                "segment_count": len(result.segments),
            },
        }
        return transcript

    def _start_attempt(self, job: ProcessingJob) -> ProcessingAttempt:
        latest = self.session.scalar(
            select(func.max(ProcessingAttempt.attempt_number)).where(
                ProcessingAttempt.job_id == job.id
            )
        )
        attempt = ProcessingAttempt(
            job_id=job.id,
            attempt_number=(latest or 0) + 1,
            status="running",
            started_at=datetime.now(UTC),
        )
        self.session.add(attempt)
        self.session.flush()
        return attempt

    def _mark_failed(
        self, source: SourceFile, job: ProcessingJob, attempt: ProcessingAttempt, message: str
    ) -> None:
        attempt.status = "failed"
        attempt.error_code = "TRANSCRIPTION_ERROR"
        attempt.error_message = message
        attempt.finished_at = datetime.now(UTC)
        job.status = "failed"
        job.metadata_json = {**job.metadata_json, "stage": "failed", "progress": 0.0}
        source.metadata_json = {**source.metadata_json, "error": message}
        self._set_status(source, "failed", 0.0)
        self.session.commit()

    @staticmethod
    def _set_status(source: SourceFile, status: str, progress: float) -> None:
        timeline = list(source.metadata_json.get("status_timeline", []))
        timeline.append({"status": status, "at": datetime.now(UTC).isoformat()})
        source.metadata_json = {
            **source.metadata_json,
            "status_timeline": timeline,
            "progress": progress,
        }
        source.ingestion_status = status
