# Local authentication

ThoughtHarbor uses local accounts and server-side sessions. No external
identity provider is required, and public registration is not exposed.

## First user

On a fresh installation, the API reports `setup_required: true` from
`GET /api/v1/auth/status`. The SvelteKit `/login` view then offers bootstrap.
The first account becomes an administrator. Once an active user exists,
`POST /api/v1/auth/bootstrap` returns `409 SETUP_COMPLETE`; additional users
register through `POST /api/v1/auth/register` and receive the `user` role.
Every authenticated resource is scoped to the current user's `owner_id`.

The first-user form asks only for a required email address, name, and password.
Usernames are not part of the registration flow.

The Compose API service runs `alembic upgrade head` before starting FastAPI.
For a host-based development API, apply migrations explicitly:

```bash
uv run --directory backend alembic upgrade head
```

## Passwords and sessions

Passwords are hashed with Argon2id. The browser receives only a cryptographically
random opaque session token in the `thought_harbor_session` cookie. The
database stores an HMAC-SHA-256 digest of that token, never the token itself.
Sessions expire after 14 days by default and logout marks them revoked.

Cookies are `HttpOnly`, `SameSite=Lax`, scoped to `/`, and use `Secure` when
`SESSION_COOKIE_SECURE=true`. Set that value for HTTPS deployments. The
session secret is supplied through `SESSION_SECRET` and must be replaced for
non-local deployments.

## CSRF and brute-force protection

State-changing authentication requests with an `Origin` header are accepted
only from `CORS_ALLOWED_ORIGINS`. SameSite cookies provide an additional
browser boundary. Login failures are throttled five times per client and
identifier in a 15-minute process-local window; a `429` response includes
`Retry-After`. This deliberately keeps the MVP dependency-light. A future
multi-process deployment should move the limiter state to the existing Redis
service.

The frontend uses the generated OpenAPI client with credentials included and
provides login, first-user bootstrap, current-user, and logout views at
`/login`.
