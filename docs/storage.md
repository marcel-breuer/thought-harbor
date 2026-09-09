# Local file storage

ThoughtHarbor stores original and derived files on the local filesystem by
default. The application accesses files through the `StorageService` port and
the `LocalFileStorage` adapter; routers, workers, and domain services do not
construct filesystem paths directly.

## Keys and layout

The adapter generates an opaque UUID-based key under one of these logical
categories:

```text
uploads/
audio/
transcripts/
documents/
derived/
```

The physical root is configured with `STORAGE_ROOT` (Compose defaults to
`/data/files`). A persisted key such as `documents/8d...` is the stable
database reference; the folder layout can change behind the adapter. Original
filenames and MIME types stay in PostgreSQL `source_files`, and are never used
as paths.

## Streaming and safety

Writes consume a binary stream in 1 MiB chunks, calculate the SHA-256 digest,
and publish through an atomic rename after the stream completes. Optional byte
limits reject oversized uploads without retaining the whole file in memory.
Reads return a binary file handle owned by the caller. Keys are restricted to
one known category and one generated identifier, resolved beneath the
configured root, and rejected if they contain traversal or absolute paths.

`validate_upload_metadata` is the hook for API-specific file size and MIME
policies. It validates the original name as metadata only; even a name that
contains path separators is never interpreted as a storage path. Uploaded
files are data, not executables, and the application does not execute them.

## Lifecycle and ownership

`SourceFile` keeps ownership, original name, MIME type, size, digest, ingestion
status, and the opaque storage key. Database soft deletion is the normal
lifecycle policy. Physical deletion is an explicit storage operation after
the application has verified ownership and any retention requirements. A
missing object is reported as a normal `False` result from deletion, while
malformed keys fail closed.

The adapter is local and volume-backed by design. The Compose `app_data`
volume is shared by API, Celery worker, and MCP processes, so they use the
same configured storage root without requiring S3 or another hosted service.
