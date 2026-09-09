# ADR-0005: Provider-independent local AI runtime

- Status: Accepted
- Date: 2026-09-09

## Context

ThoughtHarbor must work offline or on a private network by default, while
allowing operators to choose models and optionally use an OpenAI-compatible
endpoint. Domain services should not depend on vendor SDKs or provider
response formats.

## Decision

Define Python protocols/interfaces for chat/generation, structured extraction,
embeddings, and model metadata. Use Ollama as the default local adapter. Keep
an OpenAI-compatible adapter optional and explicitly configured. Vendor SDKs
remain inside adapters; application services depend only on provider ports.

Validate structured results with Pydantic before persistence. Record provider,
model, configuration/prompt version, and embedding dimension/version on
derived artifacts. Handle timeouts, cancellation, retries, and capability
errors explicitly.

## Consequences

- Switching providers does not change domain services or provenance rules.
- Local inference remains the default and no external AI account is required.
- Model downloads and CPU/GPU resource requirements need clear operations
  documentation.
- Invalid model output cannot be silently stored as trusted knowledge.
