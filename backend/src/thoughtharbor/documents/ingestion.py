"""Application service for authenticated source-file ingestion."""

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import BinaryIO, Literal, cast

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thoughtharbor.domain.models import ProcessingJob, SourceFile
from thoughtharbor.storage.service import (
    StorageService,
    StoredFile,
    validate_upload_metadata,
)

SourceType = Literal["document", "transcript", "email", "audio"]
IngestionStatus = Literal[
    "uploaded", "queued", "parsing", "transcribing", "analysing", "ready", "needs_input", "failed"
]
INGESTION_STATUSES: frozenset[str] = frozenset(
    {"uploaded", "queued", "parsing", "transcribing", "analysing", "ready", "needs_input", "failed"}
)
MAX_UPLOAD_BYTES = 50 * 1024 * 1024


class IngestionError(Exception):
    """Expected ingestion failure safe to expose through the API layer."""


class IngestionNotFoundError(IngestionError):
    """The requested source file does not belong to the current user."""


class UnsupportedSourceTypeError(IngestionError):
    """The filename or MIME type is not supported by the inbox."""


@dataclass(frozen=True, slots=True)
class IngestionPage:
    """A page of owner-scoped source files."""

    items: tuple[SourceFile, ...]
    total: int


class IngestionService:
    """Create and query inbox records without coupling them to HTTP or SvelteKit."""

    def __init__(
        self,
        session: Session,
        storage: StorageService,
        *,
        max_upload_bytes: int | None = None,
        enqueue: Callable[[int], object] | None = None,
    ) -> None:
        self.session = session
        self.storage = storage
        self.max_upload_bytes = max_upload_bytes or int(
            os.environ.get("MAX_UPLOAD_BYTES", str(MAX_UPLOAD_BYTES))
        )
        self.enqueue = enqueue or _enqueue_source_file

    def upload(
        self,
        *,
        owner_id: int,
        original_name: str,
        media_type: str | None,
        source: BinaryIO,
    ) -> SourceFile:
        """Store one upload and create its first durable processing job."""

        source_type = classify_source_type(original_name, media_type)
        stored: StoredFile | None = None
        try:
            stored = self.storage.write(source, category="uploads", max_bytes=self.max_upload_bytes)
            validate_upload_metadata(
                original_name=original_name,
                media_type=media_type,
                byte_size=stored.byte_size,
                max_bytes=self.max_upload_bytes,
                allowed_media_types=None,
            )
            timestamp = datetime.now(UTC).isoformat()
            timeline: list[dict[str, str]] = [
                {"status": "uploaded", "at": timestamp},
                {"status": "queued", "at": timestamp},
            ]
            item = SourceFile(
                owner_id=owner_id,
                storage_key=stored.storage_key,
                original_name=original_name,
                media_type=media_type,
                byte_size=stored.byte_size,
                sha256=stored.sha256,
                ingestion_status="queued",
                metadata_json={
                    "source_type": source_type,
                    "status_timeline": timeline,
                    "progress": 0.0,
                },
            )
            self.session.add(item)
            self.session.flush()
            self.session.add(
                ProcessingJob(
                    owner_id=owner_id,
                    job_type=f"{source_type}_ingestion",
                    status="queued",
                    subject_type="source_file",
                    subject_id=item.id,
                    metadata_json={"storage_key": stored.storage_key},
                )
            )
            self.session.commit()
            self.enqueue(item.id)
            self.session.refresh(item)
            return item
        except Exception:
            self.session.rollback()
            if stored is not None:
                self.storage.delete(stored.storage_key)
            raise

    def list(
        self,
        *,
        owner_id: int,
        page: int = 1,
        page_size: int = 25,
        status: str | None = None,
        source_type: str | None = None,
    ) -> IngestionPage:
        """Return only active records owned by the authenticated user."""

        statement = select(SourceFile).where(
            SourceFile.owner_id == owner_id, SourceFile.deleted_at.is_(None)
        )
        count_statement = (
            select(func.count())
            .select_from(SourceFile)
            .where(SourceFile.owner_id == owner_id, SourceFile.deleted_at.is_(None))
        )
        if status is not None:
            statement = statement.where(SourceFile.ingestion_status == status)
            count_statement = count_statement.where(SourceFile.ingestion_status == status)
        if source_type is not None:
            statement = statement.where(
                SourceFile.metadata_json["source_type"].as_string() == source_type
            )
            count_statement = count_statement.where(
                SourceFile.metadata_json["source_type"].as_string() == source_type
            )
        items = tuple(
            self.session.scalars(
                statement.order_by(SourceFile.created_at.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return IngestionPage(items=items, total=self.session.scalar(count_statement) or 0)

    def get(self, *, owner_id: int, source_file_id: int) -> SourceFile:
        """Get one owner-scoped inbox record."""

        item = self.session.scalar(
            select(SourceFile).where(
                SourceFile.id == source_file_id,
                SourceFile.owner_id == owner_id,
                SourceFile.deleted_at.is_(None),
            )
        )
        if item is None:
            raise IngestionNotFoundError("Source file not found")
        return item

    def retry(self, *, owner_id: int, source_file_id: int) -> SourceFile:
        """Requeue only a failed upload and retain the previous status history."""

        item = self.get(owner_id=owner_id, source_file_id=source_file_id)
        if item.ingestion_status != "failed":
            raise IngestionError("Only failed ingestion can be retried")
        timestamp = datetime.now(UTC).isoformat()
        timeline = list(cast(list[dict[str, str]], item.metadata_json.get("status_timeline", [])))
        timeline.append({"status": "queued", "at": timestamp})
        item.ingestion_status = "queued"
        item.metadata_json = {**item.metadata_json, "status_timeline": timeline}
        source_type = cast(SourceType, item.metadata_json.get("source_type", "document"))
        self.session.add(
            ProcessingJob(
                owner_id=owner_id,
                job_type=f"{source_type}_ingestion",
                status="queued",
                subject_type="source_file",
                subject_id=item.id,
                metadata_json={"storage_key": item.storage_key, "retry": True},
            )
        )
        self.session.commit()
        self.enqueue(item.id)
        self.session.refresh(item)
        return item


def classify_source_type(original_name: str, media_type: str | None) -> SourceType:
    """Classify supported inbox inputs without trusting the filename as a path."""

    name = original_name.casefold()
    media = (media_type or "").casefold()
    if media.startswith("audio/") or name.endswith((".mp3", ".wav", ".m4a", ".ogg", ".flac")):
        return "audio"
    if media == "message/rfc822" or name.endswith((".eml", ".msg")):
        return "email"
    if media in {"text/vtt", "application/x-subrip"} or name.endswith((".vtt", ".srt")):
        return "transcript"
    if media in {
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    } or name.endswith((".pdf", ".docx")):
        return "document"
    if (
        media.startswith("text/")
        or media in {"application/json", "application/xml"}
        or name.endswith((".txt", ".md", ".markdown", ".json", ".xml", ".csv"))
    ):
        return "transcript"
    raise UnsupportedSourceTypeError("Supported inbox types are documents, text, email, and audio")


def _enqueue_source_file(source_file_id: int) -> object:
    """Lazily import Celery so deterministic application tests need no broker."""

    from thoughtharbor.tasks.ingestion import process_source_file

    return process_source_file.delay(source_file_id)
