# ADR-0010: Route all model inference through OpenRouter

- Status: Accepted; supersedes the default-provider choice in ADR-0005
- Date: 2026-09-24

## Context

ThoughtHarbor already keeps model calls behind provider-neutral application
ports, but the local Ollama default requires large downloads and per-capability
operator configuration. The product now needs one hosted inference gateway
and a model preference each user can manage in their profile.

## Decision

- Use OpenRouter for chat, structured extraction, and embeddings. The
  deployment operator provides one `OPENROUTER_API_KEY`; backend, worker, and
  MCP processes hold it, while the browser never receives it.
- Store each user's preferred generation model on that user's profile and use
  it for chat and structured extraction, including background processing.
- Keep one deployment-wide embedding model because embeddings share a fixed
  768-dimension pgvector contract. Model changes require an explicit
  re-indexing plan.
- Remove Ollama model serving and model downloads from the Compose runtime.
- Tell users that prompts and selected source content are sent through
  OpenRouter to the provider that serves the selected model.
- Keep provider HTTP translation, validation, retries, and safe provenance in
  the provider adapter and shared runtime.

## Consequences

- A working deployment requires outbound HTTPS access and an OpenRouter key.
- The deployment operator pays for model requests made by all local users.
- Users can choose only models listed by OpenRouter as supporting text output
  and JSON-schema responses.
- Local transcription remains local and is not routed through OpenRouter.
- Derived artifacts continue to record the actual model and source evidence.
