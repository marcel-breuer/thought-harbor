#!/usr/bin/env bash
set -euo pipefail

destination="${1:-}"
if [[ -z "$destination" ]]; then
  echo "usage: scripts/backup.sh <backup-directory>" >&2
  exit 2
fi

mkdir -p "$destination"
if [[ -e "$destination/metadata.json" ]]; then
  echo "refusing to overwrite an existing backup directory" >&2
  exit 2
fi

postgres_user="${POSTGRES_USER:-thoughtharbor}"
postgres_db="${POSTGRES_DB:-thoughtharbor}"
timestamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

docker compose exec -T postgres pg_dump --format=custom --no-owner --username="$postgres_user" "$postgres_db" > "$destination/postgres.dump"
docker compose exec -T api tar -C /data -czf - . > "$destination/app_data.tar.gz"

printf '{\n  "format": "thoughtharbor-backup",\n  "version": 1,\n  "created_at": "%s",\n  "includes": ["postgres.dump", "app_data.tar.gz"]\n}\n' "$timestamp" > "$destination/metadata.json"
(cd "$destination" && sha256sum postgres.dump app_data.tar.gz metadata.json > checksums.sha256)
echo "backup written to $destination"
