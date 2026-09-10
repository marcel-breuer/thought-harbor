from io import BytesIO
from zipfile import ZipFile

import pytest

from thoughtharbor.storage.service import (
    LocalFileStorage,
    StorageKeyError,
    StorageValidationError,
    validate_upload_content,
    validate_upload_metadata,
)


def test_storage_streams_files_to_generated_non_colliding_keys(tmp_path) -> None:
    storage = LocalFileStorage(tmp_path / "files")
    first = storage.write(BytesIO(b"same name, different content"), category="uploads")
    second = storage.write(BytesIO(b"another payload"), category="uploads")

    assert first.storage_key != second.storage_key
    assert first.byte_size == len(b"same name, different content")
    assert first.sha256
    with storage.open_read(first.storage_key) as source:
        assert source.read() == b"same name, different content"
    assert (tmp_path / "files" / first.storage_key).exists()


def test_storage_rejects_traversal_and_oversized_streams(tmp_path) -> None:
    storage = LocalFileStorage(tmp_path / "files")

    with pytest.raises(StorageKeyError):
        storage.open_read("uploads/../secrets")
    with pytest.raises(StorageKeyError):
        storage.delete("/tmp/outside")
    with pytest.raises(StorageValidationError):
        storage.write(BytesIO(b"12345"), category="uploads", max_bytes=4)


def test_storage_delete_is_explicit_and_safe(tmp_path) -> None:
    storage = LocalFileStorage(tmp_path / "files")
    stored = storage.write(BytesIO(b"payload"), category="documents")

    assert storage.delete(stored.storage_key)
    assert not storage.delete(stored.storage_key)


def test_upload_metadata_validation_is_independent_from_storage_paths() -> None:
    validate_upload_metadata(
        original_name="../../meeting.mp3",
        media_type="audio/mpeg",
        byte_size=10,
        max_bytes=100,
        allowed_media_types=frozenset({"audio/mpeg"}),
    )

    with pytest.raises(StorageValidationError):
        validate_upload_metadata(
            original_name="bad\x00name.txt",
            media_type="text/plain",
            byte_size=10,
            max_bytes=100,
        )


@pytest.mark.parametrize(
    ("name", "media_type", "source_type", "payload"),
    [
        ("notes.pdf", "application/pdf", "document", b"%PDF-1.7"),
        ("recording.wav", "audio/wav", "audio", b"RIFF0000WAVE"),
        ("notes.txt", "text/plain", "transcript", b"valid UTF-8"),
    ],
)
def test_upload_content_signatures_are_checked(
    name: str, media_type: str, source_type: str, payload: bytes
) -> None:
    validate_upload_content(
        BytesIO(payload),
        original_name=name,
        media_type=media_type,
        source_type=source_type,
    )

    with pytest.raises(StorageValidationError):
        validate_upload_content(
            BytesIO(b"\xff\xfe\xff" if source_type == "transcript" else b"not the declared format"),
            original_name=name,
            media_type=media_type,
            source_type=source_type,
        )


def test_docx_container_rejects_archive_path_traversal() -> None:
    payload = BytesIO()
    with ZipFile(payload, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types />")
        archive.writestr("../../outside.txt", "untrusted")

    with pytest.raises(StorageValidationError, match="unsafe path"):
        validate_upload_content(
            BytesIO(payload.getvalue()),
            original_name="notes.docx",
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            source_type="document",
        )
