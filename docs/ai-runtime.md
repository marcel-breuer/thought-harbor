# AI runtime

Issue #14 adds a provider-independent Python runtime. Application services
depend on the ports in `thoughtharbor.ai.protocols`; only the adapters know
vendor-specific HTTP payloads. The same `AIRuntime` factory can be
constructed by FastAPI, Celery, or MCP because provider selection is not
implemented in a transport handler or task function.

## Capabilities and configuration

Chat, structured extraction, and embeddings are configured independently:

| Capability | Environment variables | Self-hosted default |
| --- | --- | --- |
| Chat | `AI_CHAT_*` | Ollama / `qwen3.8` |
| Structured extraction | `AI_EXTRACTION_*` | Ollama / `qwen3.8` |
| Embeddings | `AI_EMBEDDINGS_*` | Ollama / `qwen3-embedding:0.6b` |

`AI_DEFAULT_PROVIDER=ollama` is the default. Each capability can override it
with `AI_<CAPABILITY>_PROVIDER`. Supported values are `ollama`, `openai`,
`openai_compatible`, `anthropic`, and `gemini`. The native OpenAI, Anthropic,
and Gemini adapters use their official API endpoints by default; custom
OpenAI-compatible endpoints still require an explicit base URL. API keys are
read only by backend processes and are never included in result metadata or
logs. Anthropic and Gemini provide chat and structured extraction. Their
embedding capability can be paired with a separate Ollama or compatible
embeddings configuration.

The remaining per-capability options are `BASE_URL`, `MODEL`, `API_KEY`,
`TIMEOUT_SECONDS`, `MAX_RETRIES`, `RETRY_DELAY_SECONDS`, `CONTEXT_WINDOW`,
`MAX_OUTPUT_TOKENS`, `STRUCTURED_RETRIES`, and `MODEL_VERSION`. See
`.env.example` for the minimal local setup.

## Provider behavior

Adapters use bounded exponential retries for timeouts, connection failures,
HTTP 408, HTTP 429, and HTTP 5xx responses. Authentication, malformed
responses, and other request errors become provider-neutral errors with a
stable error code. Cancellation is not caught or retried, so worker and API
lifecycles can stop an in-flight request promptly.

The runtime estimates input tokens conservatively from message length and
rejects requests that cannot fit the configured context window and output
budget. A provider response for structured extraction is parsed with the
requested Pydantic v2 model. Invalid JSON or invalid fields is retried using
the configured structured retry count and then rejected; it is never treated
as trusted domain data.

## Provenance and metadata

Every chat, extraction, and embedding result includes `ModelMetadata` with the
provider, model, optional model version, capabilities, context limits, and a
non-secret configuration fingerprint. Application services should copy this
safe mapping into `ArtifactGeneration.metadata` alongside the normalized
`provider`, `model`, and `model_version` columns. Embedding results map to the
corresponding `Embedding` columns, including dimension and content hash.

This metadata identifies how a derived artifact was produced. It does not
replace `ArtifactSource`: derived content must still retain source chunks,
offsets, transcript timestamps, and document locations.

## Ollama setup

The Compose stack includes Ollama and persists its model cache in the
`ollama_models` volume. A companion initializer automatically pulls the
configured local models before the API, worker, and MCP services start. The
default local models are `qwen3.8` for chat and extraction and
`qwen3-embedding:0.6b` for embeddings. ThoughtHarbor requests 768-dimensional
embeddings to match its persisted vector contract. `qwen3.8` is a large local
model (about 18 GB in Ollama), so the first startup requires sufficient disk
space and memory.

External providers are opt-in per capability and are not required for a fully
self-hosted installation. When a capability is configured with an external
provider, its model is not pulled into Ollama.

## External provider examples

Use capability-specific variables so local embeddings can remain enabled while
chat or extraction is routed externally:

```dotenv
# OpenAI / ChatGPT
AI_CHAT_PROVIDER=openai
AI_CHAT_MODEL=gpt-4o-mini
AI_CHAT_API_KEY=replace-me

# Anthropic Claude
AI_EXTRACTION_PROVIDER=anthropic
AI_EXTRACTION_MODEL=claude-3-5-haiku-latest
AI_EXTRACTION_API_KEY=replace-me

# Google Gemini
AI_CHAT_PROVIDER=gemini
AI_CHAT_MODEL=gemini-2.0-flash
AI_CHAT_API_KEY=replace-me
```

Keep these values in the backend environment only; they must not be placed in
the SvelteKit public environment or browser requests.
