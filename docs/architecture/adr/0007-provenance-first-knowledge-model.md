# ADR-0007: Provenance-first knowledge model

- Status: Accepted
- Date: 2026-09-09

## Context

AI-derived summaries, decisions, tasks, questions, topics, ideas, and
statements are useful only when users can distinguish them from original
content and inspect the evidence behind them. Parsing and retrieval often
provide location metadata that is difficult to reconstruct later.

## Decision

Model original sources and derived artifacts as distinct records. Every
important derived artifact stores one or more provenance links to source
records, normalized content, chunks, or transcript segments. Preserve exact
document page/section/offset metadata and transcript timestamps/speaker
metadata through parsing, chunking, embeddings, extraction, RAG, API, UI,
and MCP.

Store provider/model/prompt metadata and controlled derived versions. A
generated citation is valid only when resolved from stored provenance. User
resolutions of uncertain AI classifications are stored separately from the
original proposal.

## Consequences

- Users can audit and navigate every important derived result back to evidence.
- Reprocessing can be controlled and compared without overwriting originals.
- The data model and API include more relationships than a summary-only
  implementation.
- Tests must assert provenance preservation across ingestion and retrieval.
