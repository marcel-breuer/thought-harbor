# Installation and operations guide

This guide is the short path for a new operator. ThoughtHarbor stores its
structured data, queues, and source files locally. OpenRouter provides chat,
structured extraction, and embeddings; AI features require an OpenRouter
account and outbound HTTPS access.

## Local development

Install Node.js 20+, pnpm 10+, Python 3.13+, uv, and Docker if integration
services are needed. From the repository root:

```bash
pnpm install --frozen-lockfile
uv sync --directory backend
cp .env.example .env
# Set OPENROUTER_API_KEY before starting AI features
uv run --directory backend alembic upgrade head
```

Start the API and web app in separate terminals:

```bash
uv run --directory backend uvicorn thoughtharbor.api.main:app --reload
pnpm --dir apps/web dev
```

Open `http://localhost:5173`. The generated OpenAPI client is in
`apps/web/src/lib/generated`; regenerate it only through the canonical
exporter and `pnpm --dir apps/web api:generate`.

## Compose installation

For the complete self-hosted stack:

```bash
cp .env.example .env
# replace SESSION_SECRET and database credentials
docker compose up -d --build
docker compose ps
```

Open `http://localhost:3000`. The API container applies Alembic migrations on
startup. The API is available locally at `http://localhost:8000` so the
production web container and the Vite dev server can use the same Docker API,
worker, and storage volume. PostgreSQL, Redis, and MCP remain internal
services. API, worker, and MCP require outbound HTTPS access to OpenRouter.
No local LLM server or model download is required.

## Configuration and secrets

`.env.example` is the complete starter reference. Important settings are:

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL`, `REDIS_URL`, `STORAGE_ROOT` | local persistence and queues |
| `SESSION_SECRET`, `SESSION_COOKIE_SECURE` | browser session protection |
| `OPENROUTER_API_KEY` | required server-side credential for AI features |
| `OPENROUTER_DEFAULT_MODEL` | deployment default for chat and extraction |
| `OPENROUTER_EMBEDDINGS_MODEL` | shared embedding model; must return 768 dimensions |
| `WHISPER_*`, `DIARIZATION_*` | local media processing and caches |
| `CLASSIFICATION_AUTO_ACCEPT_THRESHOLD` | human-review threshold |
| `MCP_API_TOKEN`, `MCP_OWNER_ID` | optional read-only MCP identity |

Users select their chat and extraction model in Profile settings. Prompts and
selected source content are sent to OpenRouter and handled by the selected
model provider. The deployment key stays in backend, worker, and MCP
environments; it must never appear in frontend configuration or logs. The
embedding model is deployment-wide because the shared vector index has a fixed
768-dimension contract.

## First user and upgrades

The first local user is created through the bootstrap/auth flow documented in
[`authentication.md`](authentication.md). Additional users can create their
own local accounts from the sign-in screen; their sources and derived
knowledge remain owner-scoped.
On upgrades, pull the new revision, review release notes, and run:

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
```

Keep named volumes stable. Alembic migrations are the source of truth for
schema changes; do not edit a live database manually.

## Backups and recovery

Use [`backup-restore.md`](backup-restore.md) for the supported checksummed
backup, explicit restore, and portable owner export commands. Test a restore
on a disposable installation before relying on it for recovery.

## Coolify and reverse proxies

Create a Compose application from this repository, set environment variables
as Coolify secrets, attach durable storage for `postgres_data`, `redis_data`,
and `app_data`, and publish only `web`. Configure the public domain and TLS at
the proxy. Keep PostgreSQL, Redis, and MCP on the private Compose network. If
remote MCP is needed, put it behind authenticated TLS and do not
place its token in committed configuration.

## Troubleshooting

- `api` is unhealthy: inspect `docker compose logs api postgres redis`, then
  check `/api/v1/ready` for the failing local dependency.
- Jobs remain queued: verify Redis health and the worker logs; retry failed
  sources from the Inbox after the queue is available.
- AI work fails: verify `OPENROUTER_API_KEY`, outbound HTTPS, and that the
  selected model supports chat or structured output as required.
- Files disappear: confirm `app_data` is durable and that `docker compose down
  -v` was not used.
- Uploads fail with a stored-source read error: inspect
  `docker compose ps -a` and confirm that `app-data-init` completed
  successfully. It prepares `/data/files` with the ownership required by the
  non-root API and worker containers.
- External deployment: verify the reverse proxy sends HTTPS, cookies are
  secure, only the web surface is public, and no secrets are browser-visible.
