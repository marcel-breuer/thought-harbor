from thoughtharbor.auth.security import (
    LoginRateLimiter,
    hash_password,
    session_token_hash,
    verify_password,
)
from thoughtharbor.auth.settings import AuthSettings


def test_passwords_use_argon2id_and_verify_without_plaintext_storage() -> None:
    password_hash = hash_password("correct-horse-battery-staple")

    assert password_hash.startswith("$argon2id$")
    assert password_hash != "correct-horse-battery-staple"
    assert verify_password(password_hash, "correct-horse-battery-staple")
    assert not verify_password(password_hash, "wrong-password")


def test_session_tokens_are_hashed_with_the_server_secret() -> None:
    settings = AuthSettings(
        session_secret="secret-a",
        cookie_secure=False,
        session_ttl_seconds=3600,
        allowed_origins=(),
    )
    token = "opaque-session-token"

    assert session_token_hash(token, settings) != token
    assert session_token_hash(token, settings) == session_token_hash(token, settings)
    assert session_token_hash(
        token,
        AuthSettings("secret-b", False, 3600, ()),
    ) != session_token_hash(token, settings)


def test_failed_login_limiter_expires_and_resets() -> None:
    limiter = LoginRateLimiter(max_attempts=2, window_seconds=60)

    assert limiter.retry_after("client:user") is None
    limiter.record_failure("client:user")
    limiter.record_failure("client:user")
    assert limiter.retry_after("client:user") is not None
    limiter.reset("client:user")
    assert limiter.retry_after("client:user") is None
