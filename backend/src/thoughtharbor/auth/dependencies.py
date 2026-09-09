"""FastAPI dependencies for database-backed authentication."""

from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.auth.service import AuthService
from thoughtharbor.auth.settings import AuthSettings
from thoughtharbor.db.session import get_db
from thoughtharbor.domain.models import User


def get_auth_settings() -> AuthSettings:
    """Load authentication configuration for one dependency resolution."""

    return AuthSettings.from_environment()


def get_auth_service(
    session: Annotated[Session, Depends(get_db)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
) -> AuthService:
    """Build the application service used by authentication routes."""

    return AuthService(session, settings)


def get_current_user(
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> User:
    """Resolve the authenticated browser session or return a safe 401."""

    user = service.current_user(request.cookies.get("thought_harbor_session"))
    if user is None:
        raise ApplicationError(
            "AUTH_REQUIRED",
            "Authentication is required.",
            status_code=401,
        )
    return user
