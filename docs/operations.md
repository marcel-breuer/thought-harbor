# Operations and reliability

ThoughtHarbor keeps operational state local. PostgreSQL is authoritative for
processing jobs and attempts; Redis is the Celery broker/result backend; no
hosted monitoring service is required.

`GET /api/v1/health` is the API liveness check. `GET /api/v1/ready` checks
PostgreSQL, Redis, writable local storage, configured AI provider endpoints,
and a responding Celery worker. It returns a safe per-dependency summary and
HTTP 503 when the stack is not ready. The authenticated settings page uses
`GET /api/v1/settings/diagnostics` to show the same summary. Docker uses the
readiness endpoint for the API healthcheck.

Workers acknowledge tasks late and reject tasks when the worker process is
lost. Celery task events and a one-hour broker visibility timeout make queued
work recoverable after a worker restart. Connection and timeout exceptions use
bounded exponential retry with jitter; permanent parser/transcription errors
are persisted as failed `ProcessingAttempt` records and can be retried from
the inbox without discarding the source.

Uploads accept an optional `Idempotency-Key`. The owner-scoped key is retained
with the source metadata so repeated requests return the existing source
instead of creating duplicate processing work. Queue outages become a visible
failed, retryable inbox state rather than an untracked upload.

Python processes emit one-line JSON logs with configurable `LOG_LEVEL`. API
request IDs and source/job IDs are included as correlation fields. Log
messages intentionally contain no document, transcript, email, credential, or
provider-key content.

`GET /metrics` exposes small in-process HTTP counters in Prometheus text
format. They are optional and reset when the process restarts; durable job
diagnosis remains in PostgreSQL and local logs.
