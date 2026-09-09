"""HTTP delivery routes for confidence-based clarification workflows."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.api.schemas import (
    ClarificationListResponse,
    ClarificationResolutionRequest,
    ClarificationResponse,
    ErrorResponse,
    KnowledgeObjectOptionResponse,
    PageMetadata,
)
from thoughtharbor.auth.dependencies import get_current_user
from thoughtharbor.db.session import get_db
from thoughtharbor.domain.models import User
from thoughtharbor.knowledge.clarifications import (
    ClarificationError,
    ClarificationService,
)

router = APIRouter(prefix="/clarifications", tags=["clarifications"])
PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Authentication is required."},
    404: {"model": ErrorResponse, "description": "The clarification does not exist."},
    422: {"model": ErrorResponse, "description": "The resolution is invalid."},
}


def get_clarification_service(
    session: Annotated[Session, Depends(get_db)],
) -> ClarificationService:
    """Build the owner-scoped clarification application service."""

    return ClarificationService(session)


@router.get(
    "",
    response_model=ClarificationListResponse,
    summary="List pending clarifications",
    responses=PRIVATE_RESPONSES,
)
def list_clarifications(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ClarificationService, Depends(get_clarification_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ClarificationListResponse:
    """Return mobile-friendly clarification cards for the authenticated owner."""

    all_items = service.list_open(user.id)
    start = (page - 1) * page_size
    items = all_items[start : start + page_size]
    total_pages = (len(all_items) + page_size - 1) // page_size if all_items else 0
    return ClarificationListResponse(
        items=[_response_for(item) for item in items],
        page=PageMetadata(
            page=page,
            page_size=page_size,
            total=len(all_items),
            total_pages=total_pages,
        ),
    )


@router.post(
    "/{clarification_id}/resolve",
    response_model=ClarificationResponse,
    summary="Resolve a clarification",
    responses=PRIVATE_RESPONSES,
)
def resolve_clarification(
    clarification_id: int,
    payload: ClarificationResolutionRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ClarificationService, Depends(get_clarification_service)],
) -> ClarificationResponse:
    """Record accept, reject, edit, assignment, or new-topic resolution."""

    try:
        item = service.resolve(
            user.id,
            clarification_id,
            action=payload.action,
            selected_knowledge_object_ids=payload.selected_knowledge_object_ids,
            new_topic_title=payload.new_topic_title,
        )
    except ClarificationError as error:
        status_code = 404 if "does not exist" in str(error) else 422
        raise ApplicationError(
            "CLARIFICATION_RESOLUTION_REJECTED", str(error), status_code=status_code
        ) from error
    return _response_for(item)


def _response_for(item: Any) -> ClarificationResponse:
    """Map application data to the stable public response schema."""

    return ClarificationResponse(
        id=item.request.id,
        question=item.request.question,
        status=item.request.status,
        classification_id=item.classification.id,
        label=item.classification.label,
        confidence=item.classification.confidence,
        source_text=item.source_chunk.text,
        source_location=item.source_chunk.location,
        options=[
            KnowledgeObjectOptionResponse.model_validate(option, from_attributes=True)
            for option in item.options
        ],
        selected_knowledge_object_ids=item.request.selected_knowledge_object_ids,
        created_at=item.request.created_at,
        resolved_at=item.request.resolved_at,
    )
