# Backup, restore, and export

## Full installation backup

With the Compose stack running, create a new destination directory and run:

```bash
scripts/backup.sh ./backups/$(date -u +%Y%m%dT%H%M%SZ)
```

The backup contains a PostgreSQL custom-format dump, the `/data` application
volume, versioned metadata, and SHA-256 checksums. It does not include Ollama
or Whisper model caches; those are reproducible downloads and can be large.
Keep the destination private because it contains original files and database
content.

## Restore

Validate and apply a backup explicitly:

```bash
scripts/restore.sh ./backups/20260910T120000Z --confirm
```

The script validates the format/version and every checksum before replacing the
database and application volume. It intentionally requires `--confirm`; stop
write-heavy workloads first and restart the API/worker after a restore if they
were running during the operation.

## Portable knowledge export

To create human-readable and machine-readable files plus copies of the owner's
original source files, use the backend environment directly:

```bash
cd backend
uv run python scripts/export_knowledge.py --owner-id 1 ../exports/marcel
```

The export contains `manifest.json` with version/count metadata,
`knowledge.json` with provenance-preserving records, `knowledge.md`, and an
`original-files/` directory. Derived records remain separate from original
source files so reprocessing cannot overwrite the source.
