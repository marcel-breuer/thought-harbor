# ThoughtHarbor threat model

ThoughtHarbor is a self-hosted application whose primary trust boundary is the
operator's installation. Uploaded documents, email bodies, transcripts,
metadata, and retrieved chunks remain untrusted data even when they contain
commands or instructions.

## Deployment profiles

| Profile | Main threats | Required controls |
| --- | --- | --- |
| Local-only | Another local process or user reads the installation | File permissions, a real session secret, durable-volume access control |
| LAN | Network peers reach the web/API surface | TLS at the proxy, allowlisted CORS origins, secure cookies, private service network |
| Internet-exposed | Credential attacks, CSRF, upload abuse, proxy misconfiguration | HTTPS, strong secrets, proxy rate limits, patched images, backups, no direct database/Redis/Ollama exposure |

PostgreSQL, Redis, Ollama, and MCP are internal Compose services by default.
Only the web service is published. Operators who expose the API or MCP server
must put them behind authenticated TLS and a network-level rate limiter.

## Assets and trust boundaries

- Account credentials, browser sessions, API token hashes, and provider keys are
  secrets. They stay server-side; logs contain request metadata only.
- Source files and derived knowledge are owner-scoped. Every private HTTP route
  resolves the current user before calling an application service; search,
  views, jobs, and MCP use the same owner-scoped services.
- Upload bytes cross into local storage through generated keys, streamed size
  limits, type classification, UTF-8/signature checks, and atomic writes.
  Original filenames are metadata, never filesystem paths. DOCX ZIP containers
  are bounded before parsing, and uploaded content is never executed.
- Retrieved evidence crosses into the AI provider as data inside explicit
  evidence delimiters. The system instruction says evidence is untrusted and
  cannot change policy, invoke tools, or create side effects. Citations are
  derived from stored chunks, not model output.
- MCP is read-only by default. Optional writes require persisted, hashed,
  owner-scoped API tokens with the requested scope and explicit
  `MCP_WRITE_ENABLED=true`.

## Controls and residual risk

Browser mutations require an allowlisted `Origin` when a session cookie is
present. CORS is explicit rather than wildcard, session cookies are HttpOnly
and SameSite=Lax, production requires a 32-character `SESSION_SECRET`, and
auth, upload, search, and chat endpoints have process-local budgets. A reverse
proxy should add shared rate limiting when more than one API process runs.

External AI providers are opt-in per capability. When enabled, source content
may leave the installation and the Settings surface warns the operator. HTML
email bodies are not rendered by the first parser; only text/plain content is
indexed. Do not treat a private self-hosted deployment as safe against a
compromised host, malicious administrators, or compromised third-party model
providers.

Security-sensitive regressions are covered by tests for owner scoping,
authentication, CSRF origins, production secret requirements, request budgets,
upload traversal/size/signature checks, bounded evidence, and server-derived
citations.
