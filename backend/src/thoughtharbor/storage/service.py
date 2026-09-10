"""Application-facing abstraction for local, volume-backed file storage."""

import os
import tempfile
import zipfile
from dataclasses import dataclass
from hashlib import sha256
from io import BytesIO
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Literal, Protocol
from uuid import uuid4

StorageCategory = Literal["uploads", "audio", "transcripts", "documents", "derived"]
STORAGE_CATEGORIES: frozenset[str] = frozenset(
    {"uploads", "audio", "transcripts", "documents", "derived"}
)
CHUNK_SIZE = 1024 * 1024


class StorageError(Exception):
    """Base class for safe storage failures exposed to application services."""


class StorageKeyError(StorageError):
    """Raised when a persisted key is malformed or escapes the storage root."""


class StorageValidationError(StorageError):
    """Raised when upload metadata or a streamed file violates policy."""


@dataclass(frozen=True, slots=True)
class StoredFile:
    """Metadata returned after an atomic storage write."""

    storage_key: str
    category: StorageCategory
    byte_size: int
    sha256: str


class StorageService(Protocol):
    """Port used by application services instead of accessing filesystem paths."""

    def write(
        self,
        source: BinaryIO,
        *,
        category: StorageCategory,
        max_bytes: int | None = None,
    ) -> StoredFile: ...

    def open_read(self, storage_key: str) -> BinaryIO: ...

    def delete(self, storage_key: str) -> bool: ...


class LocalFileStorage:
    """Store files below a configured root using generated, opaque identifiers."""

    def __init__(self, root: Path) -> None:
        self.root = root.expanduser().resolve()

    @classmethod
    def from_environment(cls) -> "LocalFileStorage":
        """Build the local adapter from the same `STORAGE_ROOT` used by Compose."""

        return cls(Path(os.environ.get("STORAGE_ROOT", ".data/files")))

    def write(
        self,
        source: BinaryIO,
        *,
        category: StorageCategory,
        max_bytes: int | None = None,
    ) -> StoredFile:
        """Stream a file to a temporary sibling and atomically publish it."""

        self._validate_category(category)
        if max_bytes is not None and max_bytes < 0:
            raise StorageValidationError("max_bytes must not be negative")

        category_root = self.root / category
        category_root.mkdir(parents=True, exist_ok=True)
        identifier = uuid4().hex
        storage_key = f"{category}/{identifier}"
        destination = self._resolve(storage_key)
        temporary_path: str | None = None
        byte_size = 0
        digest = sha256()

        try:
            file_descriptor, temporary_path = tempfile.mkstemp(
                dir=category_root,
                prefix=".upload-",
            )
            with os.fdopen(file_descriptor, "wb") as output:
                while True:
                    chunk = source.read(CHUNK_SIZE)
                    if not isinstance(chunk, bytes):
                        raise StorageValidationError("upload stream must return bytes")
                    if not chunk:
                        break
                    byte_size += len(chunk)
                    if max_bytes is not None and byte_size > max_bytes:
                        raise StorageValidationError("file exceeds the configured size limit")
                    digest.update(chunk)
                    output.write(chunk)
                output.flush()
                os.fsync(output.fileno())
            os.replace(temporary_path, destination)
            temporary_path = None
        finally:
            if temporary_path is not None:
                Path(temporary_path).unlink(missing_ok=True)

        return StoredFile(
            storage_key=storage_key,
            category=category,
            byte_size=byte_size,
            sha256=digest.hexdigest(),
        )

    def open_read(self, storage_key: str) -> BinaryIO:
        """Open a stored file after validating its key remains inside the root."""

        return self._resolve(storage_key).open("rb")

    def delete(self, storage_key: str) -> bool:
        """Delete one stored object; database soft deletion remains separate."""

        path = self._resolve(storage_key)
        try:
            path.unlink()
        except FileNotFoundError:
            return False
        return True

    def _resolve(self, storage_key: str) -> Path:
        parts = Path(storage_key).parts
        if (
            len(parts) != 2
            or parts[0] not in STORAGE_CATEGORIES
            or not parts[1]
            or parts[1] in {".", ".."}
            or Path(storage_key).is_absolute()
        ):
            raise StorageKeyError("invalid storage key")
        path = (self.root / Path(*parts)).resolve()
        if path.parent != (self.root / parts[0]).resolve():
            raise StorageKeyError("storage key escapes the configured root")
        return path

    @staticmethod
    def _validate_category(category: str) -> None:
        if category not in STORAGE_CATEGORIES:
            raise StorageValidationError("unsupported storage category")


def validate_upload_metadata(
    *,
    original_name: str,
    media_type: str | None,
    byte_size: int,
    max_bytes: int,
    allowed_media_types: frozenset[str] | None = None,
) -> None:
    """Validate caller metadata without ever using the original name as a path."""

    if not original_name or len(original_name) > 255 or "\x00" in original_name:
        raise StorageValidationError("invalid original filename")
    if byte_size < 0 or byte_size > max_bytes:
        raise StorageValidationError("file exceeds the configured size limit")
    if allowed_media_types is not None and media_type not in allowed_media_types:
        raise StorageValidationError("unsupported media type")
    if media_type in {"application/x-msdownload", "application/x-sh", "text/html"}:
        raise StorageValidationError("unsupported media type")


def validate_upload_content(
    source: BinaryIO,
    *,
    original_name: str,
    media_type: str | None,
    source_type: str,
) -> None:
    """Check lightweight signatures before an uploaded file reaches a parser."""

    raw = source.read()
    suffix = Path(original_name).suffix.casefold()
    if source_type == "transcript":
        try:
            raw.decode("utf-8-sig")
        except UnicodeDecodeError as error:
            raise StorageValidationError("text uploads must be valid UTF-8") from error
        return
    if source_type == "email":
        if b"\x00" in raw:
            raise StorageValidationError("email uploads must be text data")
        return
    if source_type == "document":
        if media_type == "application/pdf" or suffix == ".pdf":
            if not raw.startswith(b"%PDF-"):
                raise StorageValidationError("the PDF signature is invalid")
            return
        if (media_type and "wordprocessingml.document" in media_type) or suffix == ".docx":
            _validate_docx_archive(raw)
            return
    if source_type == "audio" and not _looks_like_audio(raw, suffix):
        raise StorageValidationError("the audio signature is invalid")


def _looks_like_audio(raw: bytes, suffix: str) -> bool:
    """Recognize the supported local audio containers without decoding them."""

    return (
        raw.startswith((b"ID3", b"OggS", b"fLaC", b"\x1a\x45\xdf\xa3"))
        or (raw.startswith(b"RIFF") and raw[8:12] == b"WAVE")
        or raw[:2] in {b"\xff\xfb", b"\xff\xf3", b"\xff\xf2"}
        or (len(raw) >= 12 and raw[4:8] == b"ftyp")
    )


def _validate_docx_archive(raw: bytes) -> None:
    """Reject malformed or obviously explosive DOCX ZIP containers."""

    try:
        with zipfile.ZipFile(BytesIO(raw)) as archive:
            members = archive.infolist()
            total_size = sum(member.file_size for member in members)
            if len(members) > 1_000 or total_size > 500 * 1024 * 1024:
                raise StorageValidationError("the document archive is too large")
            if any(
                PurePosixPath(member.filename).is_absolute()
                or ".." in PurePosixPath(member.filename).parts
                for member in members
            ):
                raise StorageValidationError("the document archive contains an unsafe path")
            if "[Content_Types].xml" not in archive.namelist():
                raise StorageValidationError("the DOCX container is invalid")
    except zipfile.BadZipFile as error:
        raise StorageValidationError("the DOCX container is invalid") from error
