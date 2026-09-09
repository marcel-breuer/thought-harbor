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
`http://localhost:8000/openapi.json`. Versioned REST resources use the
`/api/v1` prefix.

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

## Compose deployment

After copying `.env.example` to `.env` and replacing the local secrets, start
the self-hosted stack:

```bash
docker compose up -d --build
docker compose ps
```

The web application is available at `http://localhost:3000`. PostgreSQL,
Redis, Ollama, and the MCP process stay on the internal Compose network by
default. See [`docs/deployment/docker-compose.md`](docs/deployment/docker-compose.md)
for persistent volumes, model setup, optional GPU configuration, and Coolify.

For a portable launcher, install Docker Desktop/Engine and run the following
from the repository root. The same launcher works on Windows, macOS, and
Linux:

```text
python start.py
```

Use `py start.py` on Windows or `python3 start.py` on systems where `python`
is not the Python 3 executable. The launcher runs `docker compose up -d
--build` from the repository directory and opens `http://localhost:3000` in
the default browser after a successful start. Set `THOUGHTHARBOR_URL` to use
a different application URL.

CI and release behavior is documented in
[`docs/development/ci.md`](docs/development/ci.md).

The API contract and generated client workflow are documented in
[`docs/api/contracts.md`](docs/api/contracts.md).

Local first-user bootstrap, sessions, cookies, CSRF origin checks, and login
throttling are documented in [`docs/authentication.md`](docs/authentication.md).

The local storage abstraction, generated file keys, streaming behavior, and
filesystem safety rules are documented in [`docs/storage.md`](docs/storage.md).

The provider-independent AI runtime, local Ollama defaults, optional
OpenAI-compatible adapters, and safe generation metadata are documented in
[`docs/ai-runtime.md`](docs/ai-runtime.md).

The SQLAlchemy knowledge model, provenance rules, and migration workflow are
documented in [`docs/data-model.md`](docs/data-model.md). Apply the database
migrations before using persistence-backed features:

```bash
uv run --directory backend alembic upgrade head
```
