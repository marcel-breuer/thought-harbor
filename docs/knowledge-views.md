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

## Action knowledge

The consolidated action view keeps canonical specialized records visible across
the knowledge base:

- `GET /api/v1/knowledge/action-items` lists tasks, decisions, and open
  questions with filters for type, status, topic/project, source, assignee, and
  date.
- `GET /api/v1/knowledge/action-items/{artifact_id}` returns one item with its
  exact supporting source chunks, topic/project context, and status history.
- `PATCH /api/v1/knowledge/action-items/{artifact_id}` changes only the
  specialized record's status. The original source and AI proposal remain
  unchanged; the transition is appended to the derived artifact metadata.

Task statuses are `open`, `in_progress`, `done`, and `dismissed`. Decisions use
`active`, `superseded`, and `retracted`. Open questions use `open`, `resolved`,
and `dismissed`.

## UI behavior

The `/knowledge` SvelteKit view provides a mobile-first object overview and
detail panel. AI-derived content is labeled and visually separated from source
content. Supporting artifact records include their exact chunk context,
offsets, timestamps, and location metadata so later document and meeting
viewers can link directly to evidence.

The `/tasks` SvelteKit view provides the global action-knowledge list, summary
counts, filters, a responsive detail drawer, and status controls for the three
action types.
