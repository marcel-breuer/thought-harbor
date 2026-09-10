# Frontend content components

Shared presentational components live in `apps/web/src/lib/components` and
are exported from its `index.ts` barrel. Routes own loading, mutation, and API
state; components receive display-ready props and optional Svelte snippets.

Available patterns:

- `PageHeader` for the eyebrow, title, description, and trailing action area.
- `StatePanel` for loading, error, and empty states with accessible error
  semantics.
- `MetadataRow` for consistent definition-list metadata.
- `SourceProvenance` for original evidence and its source label.
- `AiDerivedCard` for visually distinct AI-derived content.

Visit `/components` for a lightweight gallery. Use `content-components.ts` for
shared humanization and provenance labels rather than duplicating formatting in
routes. Keep original source content and AI-derived content in separate
components so provenance remains obvious on mobile and desktop.
