# Testing guide

The normal pull-request suite is deterministic and does not download AI model
weights. Provider adapters are exercised with fakes or metadata-only checks;
model and GPU checks belong in a separately scheduled environment.

## Fast local loop

```bash
uv run --directory backend ruff check src tests
uv run --directory backend ruff format --check src tests
uv run --directory backend mypy src
uv run --directory backend pytest -q
pnpm --dir apps/web check
pnpm --dir apps/web test
pnpm --dir apps/web build
```

Backend tests cover domain/application services, parsing fixtures, storage
security, auth/session behavior, owner-scoped search and knowledge views,
provider contracts, job state transitions, MCP registration/authentication,
and OpenAPI envelopes. Frontend Vitest covers API errors, fakes, and shared
content components.

## Browser and integration checks

Playwright covers bootstrap, navigation, upload/status display, clarification
resolution, knowledge detail, search/chat citations, and mobile navigation
with deterministic API fixtures. Run it with:

```bash
pnpm --dir apps/web test:e2e
```

The CI workflow installs Chromium with operating-system dependencies. A local
PostgreSQL/Redis/Ollama Compose environment can be used for integration smoke
checks, but standard CI keeps those services internal and does not pull large
models. Before merging, also run `docker compose config --quiet` and
`scripts/check-openapi-client-drift.sh` when contracts change.
