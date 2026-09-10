# Read-only MCP

ThoughtHarbor's MCP process registers these read-only tools:

- `search_knowledge` and `ask_knowledge`
- `list_topics`, `get_topic`, `get_document`, and `get_meeting`
- `get_tasks`, `get_open_questions`, and `get_decisions`

Each tool requires the configured `MCP_API_TOKEN`. The token is compared in
constant time and resolves to the owner in `MCP_OWNER_ID`; no token is stored
or returned by the MCP adapter. Configure both values in the private Compose
environment, and do not commit them. Missing or invalid credentials return a
stable `MCP_AUTH_REQUIRED` error.

Handlers open a scoped database session and delegate to the same search, RAG,
knowledge-view, and action-item services used by FastAPI. They do not query
the database through transport code, and the default toolset contains no write
or destructive operation. Results include source chunks, locations, and
timestamps where the shared service exposes them.

Write tools are disabled by default. An operator may explicitly set
`MCP_WRITE_ENABLED=true`; only then are `update_task_status` and
`resolve_clarification` registered, and each requires a persisted API token with
the corresponding `tasks:write` or `knowledge:write` scope. These tools call
the existing action/clarification services and there is no destructive delete
tool.

For a local stdio client, use the backend module entrypoint and pass the two
environment variables from the client configuration. Keep the MCP process
inside the private network for self-hosted deployments; if it must be remote,
place it behind an authenticated TLS reverse proxy.
