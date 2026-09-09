"""Configuration for local browser authentication."""

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AuthSettings:
    """Runtime settings for session cookies, CSRF origins, and session expiry."""

    session_secret: str
    cookie_secure: bool
    session_ttl_seconds: int
    allowed_origins: tuple[str, ...]

    @classmethod
    def from_environment(cls) -> "AuthSettings":
        origins = tuple(
            origin.strip()
            for origin in os.environ.get(
                "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:5173"
            ).split(",")
            if origin.strip()
        )
        return cls(
            session_secret=os.environ.get("SESSION_SECRET", "local-development-only-change-me"),
            cookie_secure=os.environ.get("SESSION_COOKIE_SECURE", "false").lower()
            in {"1", "true", "yes", "on"},
            session_ttl_seconds=int(os.environ.get("SESSION_TTL_SECONDS", "1209600")),
            allowed_origins=origins,
        )
