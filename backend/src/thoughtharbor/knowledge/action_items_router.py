"""HTTP adapter for consolidated action-oriented knowledge views."""

from datetime import date
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.api.schemas import (
    ActionItemListResponse,
    ActionItemResponse,
    ActionItemStatusRequest,
    ActionItemSummaryResponse,
    ActionSourceResponse,
    ActionStatusHistoryResponse,
    ActionTopicResponse,
    ErrorResponse,
    PageMetadata,
    UserResponse,
)
from thoughtharbor.auth.dependencies import get_current_user
from thoughtharbor.db.session import get_db
from thoughtharbor.domain.models import User
from thoughtharbor.knowledge.action_items import (
    ActionItemError,
    ActionItemService,
    ActionItemView,
    InvalidActionItemStatusError,
)

router = APIRouter(prefix="/knowledge/action-items", tags=["knowledge"])
PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Authentication is required."},
    404: {"model": ErrorResponse, "description": "The action item does not exist."},
    422: {"model": ErrorResponse, "description": "The status is invalid."},
}


def get_service(session: Annotated[Session, Depends(get_db)]) -> ActionItemService:
    """Build the owner-scoped action-item service."""

    return ActionItemService(session)


@router.get("", response_model=ActionItemListResponse, responses=PRIVATE_RESPONSES)
def list_action_items(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ActionItemService, Depends(get_service)],
    item_type: Annotated[
        Literal["task", "decision", "open_question"] | None, Query(alias="type")
    ] = None,
    status: Annotated[str | None, Query(min_length=1, max_length=32)] = None,
    topic_id: Annotated[int | None, Query(ge=1)] = None,
    project_id: Annotated[int | None, Query(ge=1)] = None,
    source_type: Annotated[
        Literal["document", "transcript", "email", "audio"] | None, Query()
    ] = None,
    assignee_user_id: Annotated[int | None, Query(ge=1)] = None,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> ActionItemListResponse:
    """Return filtered tasks, decisions, and open questions for the owner."""

    if date_from is not None and date_to is not None and date_from > date_to:
        raise ApplicationError(
            "INVALID_DATE_RANGE", "date_from must be before date_to", status_code=422
        )
    items, total = service.list(
        user.id,
        item_type=item_type,
        status=status,
        topic_id=topic_id,
        project_id=project_id,
        source_type=source_type,
        assignee_user_id=assignee_user_id,
        date_from=date_from,
        date_to=date_to,
        page=page,
        page_size=page_size,
    )
    return ActionItemListResponse(
        items=[_response_for(item) for item in items],
        page=PageMetadata(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size if total else 0,
        ),
        summary=_summary(service.summary(user.id)),
    )


@router.get("/{artifact_id}", response_model=ActionItemResponse, responses=PRIVATE_RESPONSES)
def get_action_item(
    artifact_id: int,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ActionItemService, Depends(get_service)],
) -> ActionItemResponse:
    """Return one canonical action item and its supporting evidence."""

    try:
        return _response_for(service.get(user.id, artifact_id))
    except ActionItemError as error:
        raise ApplicationError("ACTION_ITEM_NOT_FOUND", str(error), status_code=404) from error


@router.patch("/{artifact_id}", response_model=ActionItemResponse, responses=PRIVATE_RESPONSES)
def update_action_item(
    artifact_id: int,
    payload: ActionItemStatusRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[ActionItemService, Depends(get_service)],
) -> ActionItemResponse:
    """Change a task, decision, or open-question status without changing its source."""

    try:
        return _response_for(service.update_status(user.id, artifact_id, payload.status))
    except InvalidActionItemStatusError as error:
        raise ApplicationError("INVALID_ACTION_ITEM_STATUS", str(error), status_code=422) from error
    except ActionItemError as error:
        raise ApplicationError("ACTION_ITEM_NOT_FOUND", str(error), status_code=404) from error


def _response_for(item: ActionItemView) -> ActionItemResponse:
    return ActionItemResponse(
        id=item.artifact.id,
        type=item.item_type,
        title=item.artifact.title,
        content=item.artifact.content,
        status=item.status,
        assignee=UserResponse.model_validate(item.assignee, from_attributes=True)
        if item.assignee
        else None,
        due_at=item.due_at,
        created_at=item.artifact.created_at,
        updated_at=item.artifact.updated_at,
        topics=[
            ActionTopicResponse(id=topic.id, kind=topic.kind, title=topic.title)
            for topic in item.topics
        ],
        sources=[_source(source) for source in item.sources],
        status_history=[
            ActionStatusHistoryResponse(
                status=history.status,
                previous_status=history.previous_status,
                changed_at=history.changed_at,
            )
            for history in item.status_history
        ],
    )


def _source(source: Any) -> ActionSourceResponse:
    return ActionSourceResponse(
        id=source.id,
        source_type=source.source_type,
        title=source.title,
        source_file_id=source.source_file_id,
        chunk_id=source.chunk.id,
        text=source.chunk.text,
        location=source.chunk.location,
        source_offset_start=source.chunk.source_offset_start,
        source_offset_end=source.chunk.source_offset_end,
        source_start_ms=source.chunk.source_start_ms,
        source_end_ms=source.chunk.source_end_ms,
    )


def _summary(summary: Any) -> ActionItemSummaryResponse:
    return ActionItemSummaryResponse(
        open_tasks=summary.open_tasks,
        recent_decisions=summary.recent_decisions,
        open_questions=summary.open_questions,
    )
