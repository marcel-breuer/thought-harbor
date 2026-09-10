import pytest
from pydantic import ValidationError

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.api.middleware import RequestRateLimiter
from thoughtharbor.api.schemas import BootstrapRequest, RegisterRequest
from thoughtharbor.auth.security import (
    LoginRateLimiter,
    hash_password,
    session_token_hash,
    verify_password,
)
from thoughtharbor.auth.service import AuthService
from thoughtharbor.auth.settings import AuthSettings
from thoughtharbor.domain.models import User, UserSession


class _ScalarResult:
    def __init__(self, value):
        self.value = value

    def scalar_one_or_none(self):
        return self.value


class _RegistrationSession:
    def __init__(self, active_user_id: int | None):
        self.active_user_id = active_user_id
        self.added: list[object] = []

    def execute(self, _statement):
        return _ScalarResult(self.active_user_id)

    def add(self, item):
        self.added.append(item)
        if isinstance(item, User):
            item.id = 2

    def flush(self):
        return None

    def commit(self):
        return None


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


def test_register_request_matches_bootstrap_validation() -> None:
    request = RegisterRequest(
        email="second@example.com",
        display_name=" Second ",
        password="correct-horse-battery-staple",
    )

    assert request.email == "second@example.com"
    assert request.display_name == "Second"


def test_register_creates_a_user_role_and_private_session() -> None:
    session = _RegistrationSession(active_user_id=1)
    service = AuthService(
        session, AuthSettings("secret", False, 3600, ())  # type: ignore[arg-type]
    )

    auth_session = service.register(
        email="second@example.com",
        display_name="Second User",
        password="correct-horse-battery-staple",
    )

    assert auth_session.user.role == "user"
    assert auth_session.user.email == "second@example.com"
    assert isinstance(session.added[1], UserSession)
    assert session.added[1].user_id == 2


def test_register_requires_first_admin_setup() -> None:
    session = _RegistrationSession(active_user_id=None)
    service = AuthService(
        session, AuthSettings("secret", False, 3600, ())  # type: ignore[arg-type]
    )

    with pytest.raises(ApplicationError, match="first administrator"):
        service.register(
            email="second@example.com",
            display_name="Second User",
            password="correct-horse-battery-staple",
        )

    assert session.added == []


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
