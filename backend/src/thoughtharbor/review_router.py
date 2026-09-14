"""HTTP adapters for saved searches and answer evaluations."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.api.schemas import (
    AnswerEvaluationResponse,
    ErrorResponse,
    EvaluationListResponse,
    EvaluationSummaryResponse,
    PageMetadata,
    SavedSearchCreateRequest,
    SavedSearchResponse,
    SavedSearchUpdateRequest,
)
from thoughtharbor.auth.dependencies import get_current_user
from thoughtharbor.db.session import get_db
from thoughtharbor.domain.models import User
from thoughtharbor.review import EvaluationService, SavedSearchService

router = APIRouter(tags=["review"])
PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Authentication is required."}
}


def get_saved_search_service(session: Annotated[Session, Depends(get_db)]) -> SavedSearchService:
    return SavedSearchService(session)


def get_evaluation_service(session: Annotated[Session, Depends(get_db)]) -> EvaluationService:
    return EvaluationService(session)


@router.get(
    "/saved-searches",
    response_model=list[SavedSearchResponse],
    responses=PRIVATE_RESPONSES,
)
def list_saved_searches(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedSearchService, Depends(get_saved_search_service)],
) -> list[SavedSearchResponse]:
    return [_saved_search(item) for item in service.list(user.id)]


@router.post(
    "/saved-searches",
    response_model=SavedSearchResponse,
    status_code=status.HTTP_201_CREATED,
    responses=PRIVATE_RESPONSES,
)
def create_saved_search(
    payload: SavedSearchCreateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedSearchService, Depends(get_saved_search_service)],
) -> SavedSearchResponse:
    return _saved_search(
        service.create(
            user.id,
            name=payload.name,
            query=payload.query,
            filters=payload.filters,
            enabled=payload.enabled,
        )
    )


@router.patch(
    "/saved-searches/{search_id}",
    response_model=SavedSearchResponse,
    responses={**PRIVATE_RESPONSES, 404: {"model": ErrorResponse, "description": "Not found."}},
)
def update_saved_search(
    search_id: int,
    payload: SavedSearchUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedSearchService, Depends(get_saved_search_service)],
) -> SavedSearchResponse:
    item = service.update(user.id, search_id, **payload.model_dump(exclude_unset=True))
    if item is None:
        raise ApplicationError("SAVED_SEARCH_NOT_FOUND", "Saved search not found.", status_code=404)
    return _saved_search(item)


@router.delete(
    "/saved-searches/{search_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**PRIVATE_RESPONSES, 404: {"model": ErrorResponse, "description": "Not found."}},
)
def delete_saved_search(
    search_id: int,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SavedSearchService, Depends(get_saved_search_service)],
) -> Response:
    if not service.delete(user.id, search_id):
        raise ApplicationError("SAVED_SEARCH_NOT_FOUND", "Saved search not found.", status_code=404)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/evaluations",
    response_model=EvaluationListResponse,
    responses=PRIVATE_RESPONSES,
)
def list_evaluations(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[EvaluationService, Depends(get_evaluation_service)],
    page: int = 1,
    page_size: int = 25,
) -> EvaluationListResponse:
    if page < 1 or page_size < 1 or page_size > 100:
        raise ApplicationError("INVALID_PAGINATION", "Invalid pagination.", status_code=422)
    items, total = service.list(user.id, page=page, page_size=page_size)
    summary = service.summary(user.id)
    return EvaluationListResponse(
        items=[_evaluation(item) for item in items],
        page=PageMetadata(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size if total else 0,
        ),
        summary=EvaluationSummaryResponse(
            total=summary.total,
            supported=summary.supported,
            incomplete=summary.incomplete,
            incorrect=summary.incorrect,
        ),
    )


def _saved_search(item: object) -> SavedSearchResponse:
    return SavedSearchResponse(
        id=item.id,  # type: ignore[attr-defined]
        name=item.name,  # type: ignore[attr-defined]
        query=item.query,  # type: ignore[attr-defined]
        filters=item.filters_json,  # type: ignore[attr-defined]
        enabled=item.enabled,  # type: ignore[attr-defined]
        created_at=item.created_at,  # type: ignore[attr-defined]
        updated_at=item.updated_at,  # type: ignore[attr-defined]
    )


def _evaluation(item: object) -> AnswerEvaluationResponse:
    return AnswerEvaluationResponse(
        id=item.id,  # type: ignore[attr-defined]
        conversation_id=item.conversation_id,  # type: ignore[attr-defined]
        message_id=item.message_id,  # type: ignore[attr-defined]
        rating=item.rating,  # type: ignore[attr-defined]
        notes=item.notes,  # type: ignore[attr-defined]
        created_at=item.created_at,  # type: ignore[attr-defined]
        updated_at=item.updated_at,  # type: ignore[attr-defined]
    )
