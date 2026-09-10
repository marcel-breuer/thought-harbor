#!/usr/bin/env bash
set -euo pipefail

backup_directory="${1:-}"
confirmation="${2:-}"
if [[ -z "$backup_directory" || "$confirmation" != "--confirm" ]]; then
  echo "usage: scripts/restore.sh <backup-directory> --confirm" >&2
  echo "restore replaces the current database and /data volume" >&2
  exit 2
fi
if [[ ! -d "$backup_directory" || ! -f "$backup_directory/metadata.json" || ! -f "$backup_directory/checksums.sha256" || ! -f "$backup_directory/postgres.dump" || ! -f "$backup_directory/app_data.tar.gz" ]]; then
  echo "backup is incomplete" >&2
  exit 2
fi

format="$(sed -n 's/.*"format": "\([^"]*\)".*/\1/p' "$backup_directory/metadata.json")"
version="$(sed -n 's/.*"version": \([0-9]*\).*/\1/p' "$backup_directory/metadata.json")"
if [[ "$format" != "thoughtharbor-backup" || "$version" != "1" ]]; then
  echo "unsupported or corrupt ThoughtHarbor backup metadata" >&2
  exit 2
fi

(cd "$backup_directory" && sha256sum --check checksums.sha256)
postgres_user="${POSTGRES_USER:-thoughtharbor}"
postgres_db="${POSTGRES_DB:-thoughtharbor}"

docker compose exec -T postgres pg_restore --clean --if-exists --no-owner --username="$postgres_user" --dbname="$postgres_db" < "$backup_directory/postgres.dump"
docker compose exec -T api sh -c 'find /data -mindepth 1 -maxdepth 1 -exec rm -rf -- {} + && tar -C /data -xzf -' < "$backup_directory/app_data.tar.gz"
echo "backup restored from $backup_directory"
