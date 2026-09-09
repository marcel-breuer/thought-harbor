"""Application service for queued, idempotent source-file parsing."""

from datetime import UTC, datetime
from typing import cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thoughtharbor.documents.parsing import ParsedContent, ParserError, parse_content
from thoughtharbor.domain.models import (
    ContentChunk,
    Document,
    ProcessingAttempt,
    ProcessingJob,
    SourceFile,
)
from thoughtharbor.storage.service import StorageService


class ParsingService:
    """Parse source bytes once and persist normalized, citation-ready content."""

    def __init__(self, session: Session, storage: StorageService) -> None:
        self.session = session
        self.storage = storage

    def process(self, source_file_id: int) -> Document | None:
        """Process one queued source; repeated calls do not create duplicate rows."""

        source_file = self.session.scalar(
            select(SourceFile).where(
                SourceFile.id == source_file_id, SourceFile.deleted_at.is_(None)
            )
        )
        if source_file is None:
            return None

        existing = self.session.scalar(
            select(Document).where(Document.source_file_id == source_file.id)
        )
        if existing is not None:
            self._mark_ready(source_file)
            return existing

        job = self.session.scalar(
            select(ProcessingJob)
            .where(
                ProcessingJob.subject_type == "source_file",
                ProcessingJob.subject_id == source_file.id,
            )
            .order_by(ProcessingJob.id.desc())
        )
        if job is None:
            return None
        attempt = self._start_attempt(job)
        self._set_status(source_file, "parsing", 0.0)
        self.session.commit()

        try:
            with self.storage.open_read(source_file.storage_key) as stream:
                parsed = parse_content(
                    stream,
                    original_name=source_file.original_name,
                    media_type=source_file.media_type,
                )
            document = self._persist(source_file, parsed)
        except ParserError as error:
            self._mark_failed(source_file, job, attempt, str(error))
            return None
        except OSError:
            self._mark_failed(source_file, job, attempt, "The stored source could not be read")
            return None

        attempt.status = "succeeded"
        attempt.finished_at = datetime.now(UTC)
        job.status = "succeeded"
        self._set_status(source_file, "ready", 1.0)
        self.session.commit()
        return document

    def _persist(self, source_file: SourceFile, parsed: ParsedContent) -> Document:
        metadata = {
            **source_file.metadata_json,
            "parser": {
                "name": parsed.parser_name,
                "version": parsed.parser_version,
                "metadata": parsed.metadata,
            },
        }
        title = (
            cast(str, parsed.metadata.get("subject")) if parsed.metadata.get("subject") else None
        )
        if not title:
            title = source_file.original_name.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        document = Document(
            owner_id=source_file.owner_id,
            source_file_id=source_file.id,
            title=title,
            extracted_text=parsed.text,
            metadata_json=metadata,
        )
        self.session.add(document)
        self.session.flush()
        for sequence, section in enumerate(parsed.sections):
            self.session.add(
                ContentChunk(
                    owner_id=source_file.owner_id,
                    document_id=document.id,
                    sequence=sequence,
                    text=section.text,
                    source_offset_start=section.offset_start,
                    source_offset_end=section.offset_end,
                    location=section.location,
                )
            )
        source_file.metadata_json = metadata
        return document

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
        self,
        source_file: SourceFile,
        job: ProcessingJob,
        attempt: ProcessingAttempt,
        message: str,
    ) -> None:
        attempt.status = "failed"
        attempt.error_code = "PARSER_ERROR"
        attempt.error_message = message
        attempt.finished_at = datetime.now(UTC)
        job.status = "failed"
        source_file.metadata_json = {**source_file.metadata_json, "error": message}
        self._set_status(source_file, "failed", 0.0)
        self.session.commit()

    def _mark_ready(self, source_file: SourceFile) -> None:
        if source_file.ingestion_status != "ready":
            self._set_status(source_file, "ready", 1.0)
            self.session.commit()

    @staticmethod
    def _set_status(source_file: SourceFile, status: str, progress: float) -> None:
        timestamp = datetime.now(UTC).isoformat()
        timeline = list(source_file.metadata_json.get("status_timeline", []))
        timeline.append({"status": status, "at": timestamp})
        source_file.metadata_json = {
            **source_file.metadata_json,
            "status_timeline": timeline,
            "progress": progress,
        }
        source_file.ingestion_status = status
