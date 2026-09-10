import pytest
from pydantic import ValidationError

from thoughtharbor.api.middleware import RequestRateLimiter
from thoughtharbor.api.schemas import BootstrapRequest
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


def test_bootstrap_requires_email_name_and_password() -> None:
    request = BootstrapRequest(
        email="marcel@example.com",
        display_name=" Marcel ",
        password="correct-horse-battery-staple",
    )

    assert request.email == "marcel@example.com"
    assert request.display_name == "Marcel"

    with pytest.raises(ValidationError):
        BootstrapRequest(display_name="Marcel", password="correct-horse-battery-staple")
    with pytest.raises(ValidationError):
        BootstrapRequest(
            email="marcel@example.com",
            display_name=" ",
            password="correct-horse-battery-staple",
        )


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


def test_request_rate_limiter_returns_a_retry_window() -> None:
    limiter = RequestRateLimiter()

    assert limiter.retry_after("upload:client", maximum=1, window_seconds=60) is None
    retry_after = limiter.retry_after("upload:client", maximum=1, window_seconds=60)

    assert retry_after is not None
    assert 1 <= retry_after <= 60


def test_production_requires_a_real_session_secret(monkeypatch) -> None:
    monkeypatch.setenv("TH_ENVIRONMENT", "production")
    monkeypatch.delenv("SESSION_SECRET", raising=False)

    try:
        AuthSettings.from_environment()
    except RuntimeError as error:
        assert "SESSION_SECRET" in str(error)
    else:
        raise AssertionError("production must reject the development session secret")

    monkeypatch.setenv("SESSION_SECRET", "a" * 32)
    settings = AuthSettings.from_environment()
    assert settings.cookie_secure is True
