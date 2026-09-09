# Confidence and clarification workflow

Structured extraction stores topic/project classifications as suggestions with
their confidence and source chunk. `CLASSIFICATION_AUTO_ACCEPT_THRESHOLD`
defaults to `0.85` and is configurable through the environment. A suggestion
at or above that threshold is automatically accepted only when it matches an
existing owner-scoped knowledge object. Other suggestions create an open
`ClarificationRequest` and move the source to `needs_input`.

The authenticated `GET /api/v1/clarifications` endpoint returns pending cards
with the original source text, location metadata, confidence, and available
owner-scoped topic/project choices. `POST
/api/v1/clarifications/{id}/resolve` supports accepting, rejecting, editing,
assigning multiple existing objects, and creating a new topic.

User resolutions are stored separately in the clarification request as a
timestamped JSON decision. The original AI classification remains available
for audit. Assignments add accepted owner-scoped classification records and
never modify the original document, transcript, or source chunk.
