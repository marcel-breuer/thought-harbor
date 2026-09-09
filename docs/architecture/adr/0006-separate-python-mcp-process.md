# ADR-0006: Separate Python MCP process

- Status: Accepted
- Date: 2026-09-09

## Context

MCP is a first-class interface for private AI clients, but its transport and
runtime lifecycle differ from HTTP. It must expose knowledge without creating
a second authorization or business-logic implementation.

## Decision

Use the official Python MCP SDK in a separate process/container. MCP handlers
validate tool input, authenticate the client, and call shared application and
domain services. They never access the database directly. The initial toolset
is read-only, paginated, user-scoped, and returns provenance/source metadata.

## Consequences

- MCP clients receive the same authorization, search, and provenance behavior
  as the API.
- The MCP process can be deployed locally or behind an authenticated network
  transport without changing domain services.
- Tool schemas and stable error semantics require their own contract tests.
- Mutating tools remain an explicit, scoped follow-up decision.
