"""HTTP delivery routes for local authentication."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.api.schemas import (
    AuthSessionResponse,
    AuthStatusResponse,
    BootstrapRequest,
    ErrorResponse,
    LoginRequest,
    MessageResponse,
    UserResponse,
)
from thoughtharbor.auth.dependencies import (
    get_auth_service,
    get_auth_settings,
    get_current_user,
)
from thoughtharbor.auth.security import is_allowed_origin
from thoughtharbor.auth.service import SESSION_COOKIE_NAME, AuthService
from thoughtharbor.auth.settings import AuthSettings
from thoughtharbor.auth.tokens_router import router as tokens_router
from thoughtharbor.domain.models import User

router = APIRouter(prefix="/auth", tags=["auth"])
router.include_router(tokens_router)
AUTH_ERROR_RESPONSES = {
    401: {"model": ErrorResponse, "description": "Authentication is required or invalid."},
    403: {"model": ErrorResponse, "description": "The request origin is not allowed."},
    409: {"model": ErrorResponse, "description": "The requested authentication state conflicts."},
    422: {"model": ErrorResponse, "description": "Request validation failed."},
    429: {"model": ErrorResponse, "description": "Too many authentication attempts."},
    500: {"model": ErrorResponse, "description": "Unexpected server error."},
}


@router.get(
    "/status",
    response_model=AuthStatusResponse,
    summary="Check first-user setup status",
    responses={500: AUTH_ERROR_RESPONSES[500]},
)
def auth_status(
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthStatusResponse:
    """Expose only whether bootstrap is still needed; no private data is returned."""

    return AuthStatusResponse(setup_required=service.setup_required())


@router.post(
    "/bootstrap",
    response_model=AuthSessionResponse,
    status_code=201,
    summary="Create the first local administrator",
    responses={key: AUTH_ERROR_RESPONSES[key] for key in (403, 409, 422, 500)},
)
def bootstrap(
    payload: BootstrapRequest,
    response: Response,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
) -> AuthSessionResponse:
    """Create the initial administrator; public registration remains unavailable."""

    _require_allowed_origin(request, settings)
    session = service.bootstrap(
        email=payload.email,
        username=payload.username,
        display_name=payload.display_name,
        password=payload.password,
    )
    _set_session_cookie(response, session.token, settings)
    return AuthSessionResponse(user=UserResponse.model_validate(session.user))


@router.post(
    "/login",
    response_model=AuthSessionResponse,
    summary="Log in with a local email or username",
    responses={key: AUTH_ERROR_RESPONSES[key] for key in (401, 403, 422, 429, 500)},
)
def login(
    payload: LoginRequest,
    response: Response,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
) -> AuthSessionResponse:
    """Authenticate credentials and issue an HttpOnly session cookie."""

    _require_allowed_origin(request, settings)
    client_key = request.client.host if request.client else "unknown"
    session = service.login(
        identifier=payload.identifier,
        password=payload.password,
        client_key=client_key,
    )
    _set_session_cookie(response, session.token, settings)
    return AuthSessionResponse(user=UserResponse.model_validate(session.user))


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Revoke the current local session",
    responses={key: AUTH_ERROR_RESPONSES[key] for key in (403, 500)},
)
def logout(
    response: Response,
    request: Request,
    service: Annotated[AuthService, Depends(get_auth_service)],
    settings: Annotated[AuthSettings, Depends(get_auth_settings)],
) -> MessageResponse:
    """Revoke the current session and remove its browser cookie."""

    _require_allowed_origin(request, settings)
    service.logout(request.cookies.get(SESSION_COOKIE_NAME))
    response.delete_cookie(
        SESSION_COOKIE_NAME,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )
    return MessageResponse(message="Logged out.")


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the authenticated local user",
    responses={key: AUTH_ERROR_RESPONSES[key] for key in (401, 500)},
)
def me(user: Annotated[User, Depends(get_current_user)]) -> UserResponse:
    """Return the safe profile for the current session."""

    return UserResponse.model_validate(user)


def _require_allowed_origin(request: Request, settings: AuthSettings) -> None:
    if not is_allowed_origin(request.headers.get("origin"), settings.allowed_origins):
        raise ApplicationError(
            "CSRF_ORIGIN_REJECTED",
            "The request origin is not allowed.",
            status_code=403,
        )


def _set_session_cookie(response: Response, token: str, settings: AuthSettings) -> None:
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )
