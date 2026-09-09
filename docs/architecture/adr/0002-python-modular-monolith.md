# ADR-0002: Python modular monolith

- Status: Accepted
- Date: 2026-09-09

## Context

The API, background processing, MCP, storage, AI, and knowledge workflows
share authorization, provenance, persistence, and domain policies. Splitting
these concerns into services early would duplicate contracts and add network
and deployment failure modes.

## Decision

Build one modular Python package with explicit domain/application modules.
FastAPI, Celery workers, and the MCP server are separate runtime processes
that import the same package. Application services are the single source of
business logic. Routers, task functions, and MCP handlers remain thin
adapters.

## Consequences

- Shared policies and provenance behavior cannot drift between interfaces.
- Processes can scale or restart independently within the Compose deployment.
- Module boundaries must be enforced by code review and tests.
- A future service split remains possible at a real technical boundary, but is
  not an MVP requirement.
