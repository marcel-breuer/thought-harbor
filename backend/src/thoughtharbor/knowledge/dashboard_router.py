"""HTTP adapter for the personal knowledge dashboard."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from thoughtharbor.api.schemas import (
    DashboardActionResponse,
    DashboardClarificationResponse,
    DashboardInsightResponse,
    DashboardJobResponse,
    DashboardResponse,
    DashboardSourceResponse,
    KnowledgeObjectOptionResponse,
)
from thoughtharbor.auth.dependencies import get_current_user
from thoughtharbor.db.session import get_db
from thoughtharbor.domain.models import User
from thoughtharbor.knowledge.dashboard import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


def get_dashboard_service(
    session: Annotated[Session, Depends(get_db)],
) -> DashboardService:
    return DashboardService(session)


@router.get("", response_model=DashboardResponse, summary="Get the personal knowledge dashboard")
def get_dashboard(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[DashboardService, Depends(get_dashboard_service)],
) -> DashboardResponse:
    """Return bounded persisted dashboard data for the authenticated owner."""

    view = service.get(user.id)
    return DashboardResponse(
        recent_sources=[
            DashboardSourceResponse(
                id=item.id,
                title=item.title,
                source_type=item.source_type,
                ingestion_status=item.ingestion_status,
                created_at=item.created_at,
                document_id=item.document_id,
                meeting_id=item.meeting_id,
            )
            for item in view.recent_sources
        ],
        processing_attention=[
            DashboardJobResponse.model_validate(item, from_attributes=True)
            for item in view.processing_attention
        ],
        pending_clarifications=[
            DashboardClarificationResponse.model_validate(item, from_attributes=True)
            for item in view.pending_clarifications
        ],
        open_tasks=[_action(item) for item in view.open_tasks],
        open_questions=[_action(item) for item in view.open_questions],
        recent_decisions=[_action(item) for item in view.recent_decisions],
        active_topics=[
            KnowledgeObjectOptionResponse.model_validate(item, from_attributes=True)
            for item in view.active_topics
        ],
        insights=[
            DashboardInsightResponse.model_validate(item, from_attributes=True)
            for item in view.insights
        ],
    )


def _action(item: object) -> DashboardActionResponse:
    return DashboardActionResponse.model_validate(item, from_attributes=True)
