#!/usr/bin/env bash
set -euo pipefail

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
openapi_export="${repository_root}/backend/scripts/export_openapi.py"
generated_client="${repository_root}/apps/web/src/lib/generated/openapi.json"
generated_types="${repository_root}/apps/web/src/lib/generated/api.d.ts"

if [[ ! -f "${openapi_export}" || ! -f "${generated_client}" || ! -f "${generated_types}" ]]; then
  echo "OpenAPI drift check deferred until issue #6 adds the contract artifacts."
  exit 0
fi

temporary_openapi="$(mktemp)"
trap 'rm -f "${temporary_openapi}"' EXIT

uv run --directory "${repository_root}/backend" python scripts/export_openapi.py >"${temporary_openapi}"
diff --unified=3 "${temporary_openapi}" "${generated_client}"

pnpm --dir "${repository_root}/apps/web" api:generate --silent
git -C "${repository_root}" diff --exit-code -- "${generated_types#"${repository_root}/"}"
