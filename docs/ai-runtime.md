# AI runtime

ThoughtHarbor uses a provider-independent Python runtime for chat, structured
extraction, and embeddings. All model requests go through OpenRouter from the
backend and worker processes. The SvelteKit application never contacts
OpenRouter directly.

## Configuration

Set the deployment's OpenRouter credential and optional deployment defaults in
the backend environment:

| Variable | Default | Purpose |
| --- | --- | --- |
| `OPENROUTER_API_KEY` | unset | Required server-side credential for AI features |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` | OpenRouter API origin |
| `OPENROUTER_DEFAULT_MODEL` | `openai/gpt-4o-mini` | Default chat and extraction model |
| `OPENROUTER_EMBEDDINGS_MODEL` | `openai/text-embedding-3-small` | Deployment-wide embedding model |

The selected generation model is stored on each user's profile and takes
precedence over `OPENROUTER_DEFAULT_MODEL` for chat and structured extraction,
including queued document processing. A profile with no selection uses the
deployment default. If a selected model is removed from OpenRouter, requests
fall back to the configured default and record the model reported by OpenRouter
in provenance.

Embeddings use one deployment-wide model because the shared pgvector index has
a fixed 768-dimension contract. The configured embedding model must support
the `dimensions` request parameter and return exactly 768 values. Changing the
embedding model requires an explicit re-indexing plan; vectors from different
models must not be silently mixed.

## Model selection

The authenticated `GET /api/v1/ai/models` endpoint returns models that support
text generation and JSON-schema response formats. `PATCH /api/v1/auth/me` saves
or clears the signed-in user's `preferred_ai_model`. The available-model
catalogue is requested by the backend with the deployment credential. Neither
the API key nor provider secrets are returned to users.

## Privacy and costs

Prompts and selected source content are sent to OpenRouter and forwarded to the
provider that serves the selected model. Operators should review OpenRouter's
and the underlying model provider's retention and privacy terms before
deployment. Model prices vary and may change; the profile selector shows the
current catalogue pricing when supplied by OpenRouter. The deployment
operator's OpenRouter account is charged for requests from all users.

Keep `OPENROUTER_API_KEY` in the backend environment only. Do not put it in
`PUBLIC_*` variables, browser requests, logs, result metadata, or model
configuration fingerprints.

## Provider behavior

The OpenRouter adapter sends OpenAI-compatible chat-completion and embedding
requests. Structured extraction uses strict JSON-schema responses and validates
the result with Pydantic before persistence. Bounded retries cover timeouts,
connection failures, HTTP 408, HTTP 429, and HTTP 5xx responses. Cancellation
is not caught or retried. Missing credentials, unsupported models, malformed
responses, and vector dimension mismatches produce provider-neutral errors.

The runtime checks configured context and output limits when available. Every
chat, extraction, and embedding result includes safe model metadata. Derived
artifacts retain provider/model/prompt provenance and source evidence; this
metadata does not replace `ArtifactSource`, source offsets, or transcript
timestamps.

## Local transcription

Meeting transcription continues to run locally with faster-whisper. Its model
cache remains in the application data volume. OpenRouter replaces only the
LLM and embedding runtime; it does not receive audio for transcription.
