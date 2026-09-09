# Source parsing

Issue #11 adds the shared `ParsingService` and the Celery task
`thoughtharbor.process_source_file`. The task reads the opaque local storage
key, selects a parser by the stored MIME type/extension, and persists a
normalized `Document` plus owner-scoped `ContentChunk` rows. The source file
itself is never replaced.

Supported first-iteration formats are extractable-text PDF through `pypdf`,
DOCX through `python-docx`, UTF-8 plain text/Markdown/transcript formats, and
RFC822 EML. Email headers such as subject, sender, recipients, and date are
stored as metadata. Scanned PDFs and OCR are intentionally deferred.

Each parser returns a versioned parser identity, normalized text, and sections
with offsets into that normalized text. PDF page numbers and DOCX paragraph
styles are retained in section location metadata. Chunks therefore remain
usable as provenance sources for later AI artifacts.

Processing is idempotent at the source-file boundary: if a document already
exists for a source, a repeated task does not create another document or chunk
set. Parser errors transition the source and job to `failed`, append the
actionable error to the source metadata and status timeline, and persist a
failed `ProcessingAttempt`; they do not expose document content in the error.
The inbox retry endpoint can enqueue a failed source again.
