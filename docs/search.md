# Search and indexing

Issue #17 adds one shared search application layer for the FastAPI process,
Celery workers, and future MCP tools. It does not introduce an AI service:
embedding calls go through the existing provider-neutral `AIRuntime`.

## Provenance-preserving chunks

Normalized document sections and transcript segments remain the authoritative
source chunks. The indexer creates child chunks only when a source section is
longer than the configured 1,200-character window. Child rows retain the
document offsets or transcript timestamps and record their parent and relative
offsets in `location`. The original row is marked as excluded from retrieval,
never deleted, so source and derived citations remain intact.

Chunking is deterministic and uses paragraph, sentence, and whitespace
boundaries with a 200-character overlap. The pure implementation in
`thoughtharbor.search.chunking` is usable in tests without a database or AI
provider.

## Embedding lifecycle

`SearchIndexService` batches text through the configured embeddings port and
stores provider, model, model version, dimension, and content hash with every
vector. Existing rows are reused when the content hash and model identity
match. A changed model version or provider creates a separate embedding row;
changed content updates the active row after re-embedding. The MVP vector
dimension is fixed at 768 and protected by the database constraint and HNSW
cosine index.

Source ingestion queues a `search_index` `ProcessingJob` and dispatches the
`thoughtharbor.index_source_content` Celery task. `enqueue_source(...,
force=True)` is the controlled re-index path for a model/configuration change.
The job records queued, running, succeeded, and failed stages without logging
source text.

## Retrieval and API

`SearchService` combines PostgreSQL full-text ranking (`ts_rank_cd` over the
`simple` configuration) and keyword matching with pgvector cosine similarity.
The deterministic ranking weights semantic, lexical, recency, and source-type
signals. Topic/project classification filters, date, source type, meeting,
and document filters are owner-scoped in SQL before ranking.

The authenticated endpoint is:

```text
GET /api/v1/search?q=budget&page=1&page_size=25
```

Results include the exact chunk text, source file, document/meeting context,
offsets, timestamps, and location metadata. Search can still return lexical
results if the embedding provider is temporarily unavailable; it never needs
an LLM generation call after indexing.
