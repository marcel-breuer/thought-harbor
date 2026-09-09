#!/usr/bin/env bash
set -euo pipefail

openapi_export="backend/scripts/export_openapi.py"
generated_client="apps/web/src/lib/generated/openapi.json"

if [[ ! -f "${openapi_export}" || ! -f "${generated_client}" ]]; then
  echo "OpenAPI drift check deferred until issue #6 adds the contract artifacts."
  exit 0
fi

temporary_openapi="$(mktemp)"
trap 'rm -f "${temporary_openapi}"' EXIT

uv run --directory backend python "${openapi_export}" >"${temporary_openapi}"
diff --unified=3 "${temporary_openapi}" "${generated_client}"
