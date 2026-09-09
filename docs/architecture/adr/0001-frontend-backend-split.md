# ADR-0001: Frontend/backend split and API contract

- Status: Accepted
- Date: 2026-09-09

## Context

ThoughtHarbor needs a mobile-first web interface while keeping domain logic,
authorization, persistence, and processing independent of presentation. The
frontend must not manually duplicate backend DTOs or couple itself to database
models.

## Decision

Use SvelteKit and TypeScript in `apps/web`. Use FastAPI and Pydantic v2 in the
Python backend. FastAPI/OpenAPI is the contract boundary: Pydantic schemas
produce the OpenAPI document, and a reproducible generator produces the typed
TypeScript client consumed by SvelteKit. The API is versioned under `/api/v1`.

Routers translate HTTP and delegate to application services. Svelte
components consume data-access modules and do not own business rules. Internal
SQLAlchemy models are never exposed directly.

## Consequences

- Contract changes are visible in OpenAPI and can trigger generated-client
  drift checks.
- Frontend and backend can be developed and tested independently.
- Generated code must be clearly marked and must not be edited manually.
- The API needs stable error, pagination, filtering, sorting, and request-ID
  conventions.
