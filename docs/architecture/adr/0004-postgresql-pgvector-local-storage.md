# ADR-0004: PostgreSQL, pgvector, and local filesystem storage

- Status: Accepted
- Date: 2026-09-09

## Context

The MVP needs relational knowledge, typed relationships, provenance, full-text
retrieval, embeddings, and durable original/derived files while remaining
self-hosted and easy to deploy.

## Decision

Use PostgreSQL with the pgvector extension for durable relational and vector
data. Use SQLAlchemy 2.x models and Alembic migrations. Store file bytes on a
local Docker-volume-backed filesystem behind a storage interface. Store
generated internal file IDs and metadata in PostgreSQL rather than trusting
user filenames or exposing physical paths.

Keep Pydantic API schemas separate from SQLAlchemy models. Use typed
relationship records for graph-like links; do not add a graph database.

## Consequences

- A fresh self-hosted installation owns its data without S3 or hosted vector
  services.
- PostgreSQL can combine structured, lexical, and vector retrieval.
- Backups must include both database data and the application file volume.
- Storage path layout can change without invalidating logical references.
