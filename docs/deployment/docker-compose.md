# Docker Compose deployment

ThoughtHarbor's reference deployment is a self-hosted Docker Compose stack.
It uses local persistent volumes and does not require a cloud account, S3,
hosted PostgreSQL, hosted Redis, or hosted AI provider.

## First installation

1. Install Docker Engine with the Compose plugin.
2. Clone the repository and copy the configuration template:

   ```bash
   cp .env.example .env
   ```

3. Replace `SESSION_SECRET` and the database password in `.env` with long,
   locally generated values. Keep `.env` private.
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

The published web port defaults to `3000`. PostgreSQL, Redis, Ollama, and the
MCP process are internal Compose services and are not published to the host.
The API is reachable by the web service over the internal network; operators
may add a local-only API port for diagnostics when needed.

## Services and persistent data

| Service | Purpose | Persistent volume |
| --- | --- | --- |
| `web` | SvelteKit production server | none |
| `api` | FastAPI application | `app_data` mounted at `/data` |
| `worker` | Celery processing process using the backend image | `app_data` mounted at `/data` |
| `mcp` | Official Python MCP process using the backend image | `app_data` mounted at `/data` |
| `postgres` | PostgreSQL with pgvector | `postgres_data` |
| `redis` | Celery broker/result backend and transient state | `redis_data` |
| `ollama` | Default local model runtime and model cache | `ollama_models` |

The application file volume is logically organized by the storage abstraction,
not by paths exposed to clients. Backups must include `app_data` and
`postgres_data`; model caches can be re-downloaded and do not need to be in
every backup.

## Models and CPU/GPU operation

Ollama is started by default and stores models in the persistent
`ollama_models` volume. The companion `ollama-models` service automatically
downloads the configured local models before the API, worker, and MCP services
start. The first startup can therefore take longer while model files are
downloaded.

CPU-only operation is the default. GPU support is optional and host-specific:
follow the Ollama container runtime guidance for the host's NVIDIA or other
supported runtime, add the required Compose device reservation locally, and
keep the service names, volumes, and application interfaces unchanged. Do
not make GPU hardware a prerequisite for installation.

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
and keep PostgreSQL, Redis, Ollama, and MCP internal.

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
- If Ollama is healthy but no AI work succeeds, inspect `docker compose logs
  ollama ollama-models` and verify the configured model names.
- If application files disappear after a recreate, verify that `app_data` is
  a named or durable host volume and that the deployment did not use `down -v`.
- If Coolify exposes an internal service, remove that public route and keep
  only the web reverse-proxy surface published.
