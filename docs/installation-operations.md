# Installation and operations guide

This guide is the short path for a new operator. ThoughtHarbor is local-first:
PostgreSQL/pgvector stores structured data, Redis carries Celery work, Ollama
provides the default local AI runtime, and the `app_data` volume stores source
files and model-related application data. No cloud account is required.

## Local development

Install Node.js 20+, pnpm 10+, Python 3.13+, uv, and Docker if integration
services are needed. From the repository root:

```bash
pnpm install --frozen-lockfile
uv sync --directory backend
cp .env.example .env
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
worker, and storage volume. PostgreSQL, Redis, Ollama, and MCP remain internal
services.

Ollama is included by default. The first `docker compose up` automatically
downloads the configured local chat, extraction, and embedding models and
persists them in the `ollama_models` volume. The first startup can take longer
while those model files are downloaded. CPU mode is the default.
GPU/device reservations are host-specific and optional.

## Configuration and secrets

`.env.example` is the complete starter reference. Important settings are:

| Setting | Purpose |
| --- | --- |
| `DATABASE_URL`, `REDIS_URL`, `STORAGE_ROOT` | local persistence and queues |
| `SESSION_SECRET`, `SESSION_COOKIE_SECURE` | browser session protection |
| `AI_*_PROVIDER`, `AI_*_MODEL`, `AI_*_BASE_URL` | provider/model selection |
| `AI_*_API_KEY` | optional external provider secrets; server-side only |
| `WHISPER_*`, `DIARIZATION_*` | local media processing and caches |
| `CLASSIFICATION_AUTO_ACCEPT_THRESHOLD` | human-review threshold |
| `MCP_API_TOKEN`, `MCP_OWNER_ID` | optional read-only MCP identity |

Ollama is the default and keeps content local. Setting an `AI_*_PROVIDER` to
`openai_compatible` is an explicit external-data decision; explain it to
operators and keep its key out of the frontend and logs. Provider/model changes
take effect for new API requests; worker model changes take effect when the
worker starts a new task, while cache/device changes require a worker restart.

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
the proxy. Keep PostgreSQL, Redis, Ollama, and MCP on the private Compose
network. If remote MCP is needed, put it behind authenticated TLS and do not
place its token in committed configuration.

## Troubleshooting

- `api` is unhealthy: inspect `docker compose logs api postgres redis`, then
  check `/api/v1/ready` for the failing local dependency.
- Jobs remain queued: verify Redis health and the worker logs; retry failed
  sources from the Inbox after the queue is available.
- AI work fails: inspect `docker compose logs ollama ollama-models` and confirm
  the selected model names are available.
- Files disappear: confirm `app_data` is durable and that `docker compose down
  -v` was not used.
- Uploads fail with a stored-source read error: inspect
  `docker compose ps -a` and confirm that `app-data-init` completed
  successfully. It prepares `/data/files` with the ownership required by the
  non-root API and worker containers.
- External deployment: verify the reverse proxy sends HTTPS, cookies are
  secure, only the web surface is public, and no secrets are browser-visible.
