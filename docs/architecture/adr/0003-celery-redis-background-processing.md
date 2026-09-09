# ADR-0003: Celery and Redis for background processing

- Status: Accepted
- Date: 2026-09-09

## Context

Parsing, transcription, diarization, embeddings, and AI extraction can be
slow and resource-intensive. Blocking FastAPI workers would make the mobile
application unreliable and would prevent later worker scaling.

## Decision

Use Celery with Redis as the broker/result backend and transient coordination
store. FastAPI application services create durable processing records and
enqueue idempotent jobs. Workers invoke the same application services,
persist explicit state transitions, correlation IDs, and processing attempts,
and apply bounded retry/backoff policies by error category.

PostgreSQL remains authoritative for processing state and knowledge. Redis is
not a durable domain database.

## Consequences

- Long-running work is observable and can be retried without tying up HTTP
  request workers.
- Worker replicas can be added without changing domain behavior.
- Idempotency and recovery behavior must be tested explicitly.
- A local Redis service is required by the processing stack but no hosted queue
  is required.
