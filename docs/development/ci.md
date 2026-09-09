# CI and release workflow

The repository quality gates run on pull requests and on pushes to `main`.
They are intentionally reproducible from the commands in the root README.

## Pull-request checks

- Backend dependencies are installed from the locked `uv` environment.
- Ruff linting and format verification, mypy, pytest, and an Alembic CLI sanity
  check run without downloading AI models.
- Frontend dependencies are installed from the frozen pnpm lockfile; Svelte,
  TypeScript, Vitest, and production build checks run.
- The Playwright Chromium smoke test runs in the browser-enabled CI image.
- Compose syntax is validated and both production images are built. The job
  does not pull model weights.
- OpenAPI/client drift runs through
  [`scripts/check-openapi-client-drift.sh`](../../scripts/check-openapi-client-drift.sh).
  Until issue #6 adds the exporter and generated contract artifact, the script
  emits an explicit deferred message; once both files exist, any diff fails.

Pull-request jobs receive read-only repository permissions. They do not receive
release write permissions or deployment secrets.

## Release convention

The release workflow runs only from `main` pushes or an explicit maintainer
dispatch. It creates an immutable `v0.1.<GitHub run number>` tag at the exact
main commit and publishes a GitHub release with generated notes from merged
work. It never runs on pull requests or arbitrary branch code.

The convention is intentionally simple for the bootstrap phase. A later
versioning decision may replace it with a semver policy, but must update this
document and the workflow together.

## Local equivalents

Run the fast checks from the repository root:

```bash
uv run --directory backend ruff check .
uv run --directory backend ruff format --check .
uv run --directory backend mypy src
uv run --directory backend pytest
pnpm --dir apps/web check
pnpm --dir apps/web test
pnpm --dir apps/web build
docker compose config --quiet
docker build --file docker/backend.Dockerfile --tag thought-harbor-backend:local .
docker build --file docker/web.Dockerfile --tag thought-harbor-web:local .
```

Run the browser smoke test when Chromium and its host libraries are available:

```bash
pnpm --dir apps/web exec playwright install --with-deps chromium
pnpm --dir apps/web test:e2e
```
