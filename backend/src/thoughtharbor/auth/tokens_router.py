"""HTTP adapter for user-managed scoped API tokens."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.api.schemas import (
    ApiTokenCreateRequest,
    ApiTokenListResponse,
    ApiTokenResponse,
    ErrorResponse,
    MessageResponse,
)
from thoughtharbor.auth.dependencies import get_current_user
from thoughtharbor.auth.tokens import ApiTokenService
from thoughtharbor.db.session import get_db
from thoughtharbor.domain.models import ApiToken, User

router = APIRouter(prefix="/tokens", tags=["auth"])


def get_token_service(session: Annotated[Session, Depends(get_db)]) -> ApiTokenService:
    return ApiTokenService(session)


@router.get("", response_model=ApiTokenListResponse, responses={401: {"model": ErrorResponse}})
def list_tokens(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ApiTokenService, Depends(get_token_service)],
) -> ApiTokenListResponse:
    return ApiTokenListResponse(items=[_response(token) for token in service.list(user.id)])


@router.post(
    "",
    response_model=ApiTokenResponse,
    status_code=201,
    responses={401: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
def create_token(
    payload: ApiTokenCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ApiTokenService, Depends(get_token_service)],
) -> ApiTokenResponse:
    try:
        created = service.create(
            user.id,
            name=payload.name,
            scopes=payload.scopes,
            expires_at=payload.expires_at,
        )
    except ValueError as error:
        raise ApplicationError("TOKEN_SCOPE_INVALID", str(error), status_code=422) from error
    return _response(created.token, plaintext=created.plaintext)


@router.delete(
    "/{token_id}",
    response_model=MessageResponse,
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def revoke_token(
    token_id: int,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ApiTokenService, Depends(get_token_service)],
) -> MessageResponse:
    if not service.revoke(user.id, token_id):
        raise ApplicationError("TOKEN_NOT_FOUND", "The API token does not exist.", status_code=404)
    return MessageResponse(message="API token revoked.")


def _response(token: ApiToken, *, plaintext: str | None = None) -> ApiTokenResponse:
    return ApiTokenResponse(
        id=token.id,
        name=token.name,
        token_prefix=token.token_prefix,
        scopes=token.scopes,
        expires_at=token.expires_at,
        last_used_at=token.last_used_at,
        created_at=token.created_at,
        token=plaintext,
    )
