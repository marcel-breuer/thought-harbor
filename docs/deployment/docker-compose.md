# Docker Compose deployment

ThoughtHarbor's reference deployment is a self-hosted Docker Compose stack.
PostgreSQL, Redis, and file storage remain local. AI features require an
OpenRouter account, a server-side API key, and outbound HTTPS access.

## First installation

1. Install Docker Engine with the Compose plugin.
2. Clone the repository and copy the configuration template:

   ```bash
   cp .env.example .env
   ```

3. Replace `SESSION_SECRET` and the database password in `.env` with long,
   locally generated values. Set `OPENROUTER_API_KEY` and keep `.env` private.
4. Start the stack with the portable launcher:

   ```bash
   python start.py
   docker compose ps
   ```

   Use `py start.py` on Windows or `python3 start.py` where `python` is not
   the Python 3 executable. The launcher works from any current directory and
   runs `docker compose up -d --build` from the repository root and opens
   `http://localhost:3000` in the default browser after a successful start.
   Set `THOUGHTHARBOR_URL` to override the URL.

The published web port defaults to `3000`. The API is also bound to
`127.0.0.1:8000` by default so browser requests from the web UI and a local
Vite dev server reach the same API and storage volume as the worker. Override
the host port with `API_PORT` if needed. PostgreSQL, Redis, and MCP remain
internal Compose services. API, worker, and MCP require outbound HTTPS access
to OpenRouter.

## Services and persistent data

| Service | Purpose | Persistent volume |
| --- | --- | --- |
| `app-data-init` | Initializes ownership and directories for the application volume | `app_data` mounted at `/data` |
| `web` | SvelteKit production server | none |
| `api` | FastAPI application | `app_data` mounted at `/data` |
| `worker` | Celery processing process using the backend image | `app_data` mounted at `/data` |
| `mcp` | Official Python MCP process using the backend image | `app_data` mounted at `/data` |
| `postgres` | PostgreSQL with pgvector | `postgres_data` |
| `redis` | Celery broker/result backend and transient state | `redis_data` |

The application file volume is logically organized by the storage abstraction,
not by paths exposed to clients. Backups must include `app_data` and
`postgres_data`; model caches can be re-downloaded and do not need to be in
every backup.

## OpenRouter model settings

Set `OPENROUTER_API_KEY` in `.env` or the deployment secret store. The default
generation model can be changed with `OPENROUTER_DEFAULT_MODEL`; each user can
choose a supported chat and structured-output model from Profile settings.
`OPENROUTER_EMBEDDINGS_MODEL` is deployment-wide and must support 768 output
dimensions. Changing it requires re-indexing all stored source chunks.

Prompts and selected source content are sent to OpenRouter and handled by the
provider serving the selected model. Review both providers' privacy and data
retention terms. The deployment account pays for requests from all users.

## Operations

```bash
docker compose logs -f api worker
docker compose ps
docker compose restart worker
docker compose down
```

Do not use `docker compose down -v` unless all persistent data is intentionally
being removed. The named volumes survive normal stop, restart, and recreate
operations.

## Coolify

Create a Compose-based application in Coolify pointing at the repository and
use the repository's `compose.yml`. Configure the environment variables in
Coolify's secret/environment settings rather than committing them. Publish
only the `web` service through the Coolify proxy, configure its domain and TLS,
and keep PostgreSQL, Redis, and MCP internal. Configure outbound HTTPS for the
API, worker, and MCP services.

Ensure Coolify provides persistent storage for the named volumes or maps them
to durable host paths. Keep the same volume names across redeployments and
confirm that the deployment user can read/write `app_data`. For a GPU host,
apply the host runtime/device configuration explicitly; CPU-first deployments
need no device mapping.

The MCP service runs the read-only MCP implementation. Configure `MCP_API_TOKEN`
and `MCP_OWNER_ID` in the private environment before connecting a client. The
MCP process remains internal to Compose; expose it through an authenticated
reverse proxy only when a remote transport is required.

## Troubleshooting

- If `api` waits, inspect `docker compose ps` and the PostgreSQL/Redis health
  checks before restarting application services.
- If AI work or the profile model list is unavailable, check that
  `OPENROUTER_API_KEY` is valid, outbound HTTPS is allowed, and the selected
  model remains available on OpenRouter.
- If application files disappear after a recreate, verify that `app_data` is
  a named or durable host volume and that the deployment did not use `down -v`.
- If `api` reports that local storage is unavailable or uploads fail with a
  stored-source read error, inspect `docker compose ps -a` and confirm that
  `app-data-init` completed successfully. It initializes `/data/files` and
  gives the non-root API, worker, and MCP processes access to the shared
  volume.
- If Coolify exposes an internal service, remove that public route and keep
  only the web reverse-proxy surface published. Set the API port/binding to
  match the reverse-proxy setup when browser clients need direct API access.
