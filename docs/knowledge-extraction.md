# Structured knowledge extraction

After parsing a document or transcribing a meeting, the Celery source task
invokes the shared `KnowledgeExtractionService`. The service uses the AI
provider abstraction and a Pydantic schema; it does not put provider-specific
logic in a task or API route.

The model returns one or more artifacts such as summaries, decisions, tasks,
open questions, statements, ideas, suggestions, and topic/project
classifications. Every artifact must contain one or more `source_chunk_ids`.
The service validates that those IDs belong to the owner-scoped source before
writing anything. Invalid provider output is recorded as a failed processing
attempt and cannot create partial derived records.

Artifacts are stored separately from original documents and transcripts in
`derived_artifacts`. `artifact_sources` links each artifact to its supporting
content chunk and keeps a short supporting excerpt. Decisions, tasks, open
questions, and ideas additionally receive their first-class domain row.
Classifications remain suggestions and are linked to an exact owner-scoped
knowledge object when one exists.

Each extraction run records provider/model metadata, prompt name/version, a
pipeline version, a run ID, and a monotonically increasing source version.
Reprocessing creates a new version and marks the previous source artifacts as
inactive with `superseded_by` references. Original source records are never
overwritten.

Meeting transcript segments are materialized as content chunks on first
extraction, retaining their start/end timestamps. Document parser chunks keep
their page, section, and character-offset metadata. This makes provenance
available to later semantic search, UI citations, RAG, and MCP consumers.

The extraction prompt is intentionally versioned in code. Changes to its
instructions or output schema should increment `PROMPT_VERSION` and be
reviewed as a controlled reprocessing change.
