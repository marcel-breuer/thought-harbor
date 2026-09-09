# Grounded RAG chat

Issue #18 adds the `RAGService` used by the HTTP chat adapter and future MCP
tools. It retrieves through `SearchService`, assembles bounded evidence, and
uses the configured `AIRuntime` chat capability. There is no separate AI
microservice.

## Evidence and security

Retrieved files, emails, and transcripts are inserted into explicitly marked
`<evidence>` blocks after the system instructions. The system prompt treats
those blocks as untrusted data: their text cannot invoke tools, change policy,
or override the assistant's behavior. Only server-side `SearchHit` provenance
creates citation records; model-generated locations are never trusted.

When no result reaches `RAG_MIN_EVIDENCE_SCORE`, the service stores the user
question and returns a clear insufficient-evidence response without making a
generation call. Context is bounded by `RAG_MAX_CONTEXT_CHARS` and
`RAG_MAX_RESULTS` (defaults: 12,000 characters and 8 results).

## Conversations

Conversations and messages are owner-scoped PostgreSQL records. A supplied
conversation ID is accepted only when it belongs to the current user. Assistant
messages store the exact server-derived citation metadata and whether evidence
was sufficient. The service sends only the latest bounded history to the
provider.

## API and UI

The authenticated endpoint is:

```text
POST /api/v1/chat
{
  "question": "What did we decide about the launch?",
  "conversation_id": 42,
  "source_type": "transcript",
  "project_id": 7
}
```

The response contains the answer, conversation/message IDs, an explicit
`evidence_sufficient` flag, and citations linking each marker to a chunk and
its exact excerpt plus document or meeting offsets/timestamps. The mobile-first SvelteKit chat
surface is available at `/chat`. Streaming is intentionally left behind the
provider port: the current Ollama and OpenAI-compatible adapters use the safe
request/response path, so enabling streaming later does not move RAG logic out
of the shared application service.
