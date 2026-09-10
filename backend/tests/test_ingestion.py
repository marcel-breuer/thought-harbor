"""Unit tests for source classification and inbox application behavior."""

from datetime import datetime
from io import BytesIO
from typing import Any

import pytest

from thoughtharbor.documents.ingestion import (
    IngestionService,
    UnsupportedSourceTypeError,
    classify_source_type,
)
from thoughtharbor.domain.models import ProcessingJob, SourceFile
from thoughtharbor.storage.service import StorageValidationError, StoredFile


@pytest.mark.parametrize(
    ("name", "media_type", "expected"),
    [
        ("notes.pdf", "application/pdf", "document"),
        ("meeting.txt", "text/plain", "transcript"),
        ("mail.eml", "message/rfc822", "email"),
        ("recording.wav", "audio/wav", "audio"),
        ("captions.srt", None, "transcript"),
    ],
)
def test_classify_supported_inbox_sources(name: str, media_type: str | None, expected: str) -> None:
    assert classify_source_type(name, media_type) == expected


def test_unknown_source_type_is_rejected() -> None:
    with pytest.raises(UnsupportedSourceTypeError):
        classify_source_type("archive.exe", "application/octet-stream")


def test_upload_creates_queued_owner_scoped_source_and_job() -> None:
    session = FakeSession()
    storage = FakeStorage()
    service = IngestionService(session, storage, max_upload_bytes=100, enqueue=lambda _: None)

    item = service.upload(
        owner_id=42,
        original_name="meeting.txt",
        media_type="text/plain",
        source=BytesIO(b"hello"),
    )

    assert item.id == 7
    assert item.owner_id == 42
    assert item.ingestion_status == "queued"
    assert item.metadata_json["source_type"] == "transcript"
    assert [event["status"] for event in item.metadata_json["status_timeline"]] == [
        "uploaded",
        "queued",
    ]
    job = next(value for value in session.added if isinstance(value, ProcessingJob))
    assert job.owner_id == 42
    assert job.subject_id == 7
    assert storage.deleted == []


def test_upload_removes_file_when_metadata_is_invalid() -> None:
    session = FakeSession()
    storage = FakeStorage()
    service = IngestionService(session, storage, max_upload_bytes=100, enqueue=lambda _: None)

    with pytest.raises(StorageValidationError):
        service.upload(
            owner_id=42,
            original_name="",
            media_type="text/plain",
            source=BytesIO(b"hello"),
        )

    assert len(storage.deleted) == 1
    assert session.rolled_back is True


class FakeStorage:
    def __init__(self) -> None:
        self.deleted: list[str] = []
        self.payload = b"hello"

    def write(self, source: Any, *, category: str, max_bytes: int | None = None) -> StoredFile:
        data = source.read()
        assert category == "uploads"
        assert max_bytes is None or len(data) <= max_bytes
        return StoredFile("uploads/test-key", "uploads", len(data), "a" * 64)

    def open_read(self, storage_key: str) -> Any:
        assert storage_key == "uploads/test-key"
        return BytesIO(self.payload)

    def delete(self, storage_key: str) -> bool:
        self.deleted.append(storage_key)
        return True


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.rolled_back = False

    def add(self, value: Any) -> None:
        self.added.append(value)

    def flush(self) -> None:
        source = next(value for value in self.added if isinstance(value, SourceFile))
        source.id = 7

    def commit(self) -> None:
        pass

    def refresh(self, value: Any) -> None:
        if isinstance(value, SourceFile):
            value.created_at = value.updated_at = datetime.now()

    def rollback(self) -> None:
        self.rolled_back = True
