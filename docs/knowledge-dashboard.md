# Personal knowledge dashboard

`GET /api/v1/dashboard` provides the authenticated owner's bounded dashboard
read model. It includes recent sources, active or failed processing jobs,
pending clarifications, open tasks and questions, recent decisions, and the
most recently updated topics and projects.

The endpoint only reads persisted records and caps each collection at six
items. It never invokes an AI provider during a page request. The `insights`
collection is reserved for opt-in, asynchronously generated suggestions; the
dashboard labels those records as AI-derived when they are available.

The SvelteKit landing page refreshes the read model on demand and every 30
seconds while open. Source cards link to the inbox or to owner-scoped document
and meeting views, while attention cards link to the relevant workflow.
