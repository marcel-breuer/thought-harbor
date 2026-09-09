"""Password, session-token, CSRF-origin, and login-throttling primitives."""

import hmac
import secrets
import time
from collections import defaultdict, deque
from collections.abc import Iterable
from hashlib import sha256
from threading import Lock

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError

from thoughtharbor.auth.settings import AuthSettings

PASSWORD_HASHER = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)
_dummy_password_hash: str | None = None


def hash_password(password: str) -> str:
    """Hash a password with Argon2id using memory-hard parameters."""

    return PASSWORD_HASHER.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    """Verify a password while using a dummy hash for unknown identifiers."""

    global _dummy_password_hash
    if password_hash is None:
        if _dummy_password_hash is None:
            _dummy_password_hash = hash_password(secrets.token_urlsafe(32))
        password_hash = _dummy_password_hash
    try:
        return PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerifyMismatchError):
        return False


def new_session_token() -> str:
    """Generate an opaque token that is only returned to the browser cookie."""

    return secrets.token_urlsafe(32)


def session_token_hash(token: str, settings: AuthSettings) -> str:
    """Hash a session token with the server secret before database storage."""

    return hmac.new(
        settings.session_secret.encode("utf-8"), token.encode("utf-8"), sha256
    ).hexdigest()


def is_allowed_origin(origin: str | None, allowed_origins: Iterable[str]) -> bool:
    """Allow non-browser clients and explicitly configured same-site origins."""

    return origin is None or origin in allowed_origins


class LoginRateLimiter:
    """Process-local fixed-window limiter for failed login attempts."""

    def __init__(self, *, max_attempts: int = 5, window_seconds: int = 900) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def retry_after(self, key: str) -> int | None:
        """Return remaining lockout seconds, or None when another attempt is allowed."""

        now = time.monotonic()
        with self._lock:
            failures = self._failures[key]
            self._discard_expired(failures, now)
            if len(failures) < self.max_attempts:
                return None
            return max(1, int(self.window_seconds - (now - failures[0])))

    def record_failure(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            failures = self._failures[key]
            self._discard_expired(failures, now)
            failures.append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def _discard_expired(self, failures: deque[float], now: float) -> None:
        while failures and now - failures[0] >= self.window_seconds:
            failures.popleft()
