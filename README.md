# ThoughtHarbor

ThoughtHarbor is a self-hosted, mobile-first second brain for meetings,
documents, transcripts, emails, and structured knowledge.

Architecture and implementation documentation lives in [`docs/`](docs/).

## Repository layout

```text
apps/web                  SvelteKit frontend
backend/src/thoughtharbor Shared Python package for API, worker, and MCP
backend/tests             Python tests
docs                      Architecture and operational documentation
docker                    Container assets
compose.yml               Self-hosted deployment (added in #4)
```

## Prerequisites

- Node.js 20+ and pnpm 10+
- Python 3.13+ and uv
- Docker Engine and Docker Compose for the full stack

The current bootstrap starts the web and API processes independently. The
Compose stack is introduced in issue #4.

## Bootstrap

```bash
pnpm install --frozen-lockfile
uv sync --directory backend
cp .env.example .env
```

Start the development processes in separate terminals:

```bash
pnpm --dir apps/web dev
uv run --directory backend uvicorn thoughtharbor.api.main:app --reload
```

The web app runs at `http://localhost:5173`; the API runs at
`http://localhost:8000`, with its OpenAPI document at
`http://localhost:8000/openapi.json`.

## Quality commands

```bash
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
uv run --directory backend mypy src
uv run --directory backend pytest
pnpm --dir apps/web check
pnpm --dir apps/web test
pnpm --dir apps/web build
```

The frontend package also provides `test:e2e` for the Playwright smoke suite.
The full multi-service test environment and CI are added by later issues.
