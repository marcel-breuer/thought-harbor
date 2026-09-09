# API contracts

FastAPI and its Pydantic v2 schemas are the source of truth for the public
ThoughtHarbor API. The OpenAPI document is exported from the application and
then used to generate the SvelteKit client. Frontend code must not recreate
backend request or response DTOs by hand.

## Versioning

REST resources live below `/api/v1`. The unversioned `/health` endpoint is kept
outside the OpenAPI document solely for Docker health checks. It is not a
frontend or integration contract.

Breaking changes require an explicit API versioning decision. Additive changes
should preserve existing fields and meanings.

## Errors

Every API error uses this envelope:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request could not be validated.",
    "details": [
      {
        "location": ["query", "page"],
        "message": "Input should be greater than or equal to 1",
        "type": "greater_than_equal"
      }
    ]
  },
  "request_id": "correlation-id"
}
```

`error.code` is stable for programmatic handling. Validation details are
optional and never include sensitive request bodies. Unexpected failures use
`INTERNAL_ERROR` without exposing implementation details. Every response also
contains the `X-Request-ID` header; an incoming safe ID is retained, otherwise
the API generates one.

## Collection conventions

Future collection endpoints use these query parameters:

- `page`: one-based page number, default `1`
- `page_size`: number of records, default `25`, maximum `100`
- `search`: optional text filter, maximum 200 characters
- `sort_by`: public resource field in `snake_case`
- `sort_order`: `asc` or `desc`, default `asc`

Collection responses should return `items` and page metadata containing
`page`, `page_size`, `total`, and `total_pages`. Resource-specific filters must
be explicit typed parameters; arbitrary SQL field names are not accepted.

## Client generation

From the repository root:

```bash
uv run --directory backend python scripts/export_openapi.py > \
  apps/web/src/lib/generated/openapi.json
pnpm --dir apps/web api:generate
```

The generated files are committed so frontend builds are independent of a
running API. `openapi-fetch` provides the typed runtime client through
[`apps/web/src/lib/api/client.ts`](../../apps/web/src/lib/api/client.ts).
Generated files must not be edited manually. The CI drift check regenerates
OpenAPI and fails when the committed contract differs.

The frontend uses thin service modules under `apps/web/src/lib/api/services`
for domain-specific behavior. Components do not construct API URLs or call
`fetch` directly. Services accept an optional `AbortSignal`, normalize the
public error envelope into `ApiClientError`, and share the client’s
`credentials: include` and authentication-expiry behavior. The public base URL
is the only frontend environment value; secrets remain server-side.

Use SvelteKit server `load` functions and form actions for SSR-safe initial
data and mutations. Use the browser service modules for interactive requests
that need cancellation or immediate updates. TanStack Query is intentionally
not installed yet: the current contract has no client-side caching or
background-refetch use case. Add it only when a concrete screen benefits from
those behaviors.

## Layering

FastAPI routers are delivery adapters. They validate input, call an explicit
application/domain service, and serialize the service result through Pydantic
schemas. SQLAlchemy models and database sessions must not be exposed directly
as public DTOs.
