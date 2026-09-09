"""Application service for first-user setup and local browser sessions."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.auth.security import (
    LoginRateLimiter,
    hash_password,
    new_session_token,
    session_token_hash,
    verify_password,
)
from thoughtharbor.auth.settings import AuthSettings
from thoughtharbor.domain.models import User, UserSession

SESSION_COOKIE_NAME = "thought_harbor_session"
INVALID_CREDENTIALS_MESSAGE = "Invalid credentials."


@dataclass(frozen=True, slots=True)
class AuthSession:
    """A user and the one-time plaintext token for its browser cookie."""

    user: User
    token: str


class AuthService:
    """Coordinate authentication policies and persistence operations."""

    def __init__(
        self,
        session: Session,
        settings: AuthSettings,
        *,
        rate_limiter: LoginRateLimiter | None = None,
    ) -> None:
        self.session = session
        self.settings = settings
        self.rate_limiter = rate_limiter or login_rate_limiter

    def setup_required(self) -> bool:
        """Return whether an active user still needs to be bootstrapped."""

        user_id = self.session.execute(
            select(User.id).where(User.deleted_at.is_(None)).limit(1)
        ).scalar_one_or_none()
        return user_id is None

    def bootstrap(
        self,
        *,
        email: str | None,
        username: str | None,
        display_name: str | None,
        password: str,
    ) -> AuthSession:
        """Create the sole initial administrator and establish its session."""

        if not self.setup_required():
            raise ApplicationError(
                "SETUP_COMPLETE",
                "The initial user has already been created.",
                status_code=409,
            )
        if email is None and username is None:
            raise ApplicationError("IDENTIFIER_REQUIRED", "Provide an email address or username.")

        user = User(
            email=_normalise_optional(email),
            username=_normalise_optional(username),
            password_hash=hash_password(password),
            role="admin",
            display_name=display_name.strip() if display_name else None,
        )
        self.session.add(user)
        try:
            self.session.flush()
        except IntegrityError as exc:
            self.session.rollback()
            raise ApplicationError(
                "BOOTSTRAP_CONFLICT",
                "That email address or username is already in use.",
                status_code=409,
            ) from exc
        return self._create_session(user)

    def login(self, *, identifier: str, password: str, client_key: str) -> AuthSession:
        """Authenticate an email/username and create a revocable session."""

        key = f"{client_key}:{_normalise(identifier)}"
        retry_after = self.rate_limiter.retry_after(key)
        if retry_after is not None:
            raise ApplicationError(
                "AUTH_RATE_LIMITED",
                "Too many failed login attempts. Try again later.",
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )

        normalised_identifier = _normalise(identifier)
        user = self.session.execute(
            select(User)
            .where(
                User.deleted_at.is_(None),
                or_(
                    func.lower(User.email) == normalised_identifier,
                    func.lower(User.username) == normalised_identifier,
                ),
            )
            .limit(1)
        ).scalar_one_or_none()
        if user is None or not verify_password(user.password_hash if user else None, password):
            self.rate_limiter.record_failure(key)
            raise ApplicationError(
                "AUTH_INVALID_CREDENTIALS",
                INVALID_CREDENTIALS_MESSAGE,
                status_code=401,
            )

        self.rate_limiter.reset(key)
        return self._create_session(user)

    def current_user(self, token: str | None) -> User | None:
        """Resolve a non-expired, non-revoked session token to its user."""

        if not token:
            return None
        now = datetime.now(UTC)
        token_hash = session_token_hash(token, self.settings)
        return self.session.execute(
            select(User)
            .join(UserSession, UserSession.user_id == User.id)
            .where(
                User.deleted_at.is_(None),
                UserSession.deleted_at.is_(None),
                UserSession.token_hash == token_hash,
                UserSession.expires_at > now,
            )
            .limit(1)
        ).scalar_one_or_none()

    def logout(self, token: str | None) -> None:
        """Revoke a session without exposing whether a token was valid."""

        if token:
            self.session.execute(
                update(UserSession)
                .where(
                    UserSession.token_hash == session_token_hash(token, self.settings),
                    UserSession.deleted_at.is_(None),
                )
                .values(deleted_at=datetime.now(UTC))
            )
            self.session.commit()

    def _create_session(self, user: User) -> AuthSession:
        token = new_session_token()
        self.session.add(
            UserSession(
                user_id=user.id,
                token_hash=session_token_hash(token, self.settings),
                expires_at=datetime.now(UTC) + timedelta(seconds=self.settings.session_ttl_seconds),
            )
        )
        self.session.commit()
        return AuthSession(user=user, token=token)


def _normalise(value: str) -> str:
    return value.strip().casefold()


def _normalise_optional(value: str | None) -> str | None:
    return _normalise(value) if value else None


login_rate_limiter = LoginRateLimiter()
