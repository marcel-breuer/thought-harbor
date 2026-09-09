from io import BytesIO

import pytest

from thoughtharbor.storage.service import (
    LocalFileStorage,
    StorageKeyError,
    StorageValidationError,
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
