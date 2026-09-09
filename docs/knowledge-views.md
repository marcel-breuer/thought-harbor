# Knowledge views

Issue #19 adds owner-scoped read models for the human-facing knowledge layer.
The API keeps original source content and AI-derived artifacts separate while
returning their explicit provenance links together.

## API surface

- `GET /api/v1/knowledge/objects` lists topics, projects, people, and custom
  knowledge objects with pagination and optional kind filtering.
- `GET /api/v1/knowledge/objects/{id}` returns related objects, derived
  artifacts, and every supporting source chunk.
- `PATCH /api/v1/knowledge/objects/{id}` permits an owner to correct a title.
- `GET /api/v1/knowledge/documents/{id}` returns original filename/media type,
  extracted text, parser metadata, source chunks, and derived artifacts.
- `GET /api/v1/knowledge/meetings/{id}` returns audio/source metadata,
  timestamped transcript segments, speaker labels, and derived artifacts.

Every endpoint is authenticated and owner-scoped. A missing or foreign ID is
reported as not found, so resource existence is not disclosed across users.

## UI behavior

The `/knowledge` SvelteKit view provides a mobile-first object overview and
detail panel. AI-derived content is labeled and visually separated from source
content. Supporting artifact records include their exact chunk context,
offsets, timestamps, and location metadata so later document and meeting
viewers can link directly to evidence.
