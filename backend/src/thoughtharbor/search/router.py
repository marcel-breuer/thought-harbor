"""HTTP adapter for the shared hybrid search service."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from thoughtharbor.api.middleware import rate_limit_dependency
from thoughtharbor.api.schemas import (
    ErrorResponse,
    PageMetadata,
    SearchListResponse,
    SearchResultResponse,
)
from thoughtharbor.auth.dependencies import get_current_user
from thoughtharbor.db.session import get_db
from thoughtharbor.domain.models import User
from thoughtharbor.search.service import SearchFilters, SearchService

router = APIRouter(prefix="/search", tags=["search"])


def get_search_service(
    session: Annotated[Session, Depends(get_db)],
) -> SearchService:
    """Build the shared search application service."""

    return SearchService(session)


@router.get(
    "",
    response_model=SearchListResponse,
    summary="Search indexed knowledge",
    responses={401: {"model": ErrorResponse, "description": "Authentication is required."}},
    dependencies=[Depends(rate_limit_dependency("search"))],
)
async def search(
    query: Annotated[str, Query(alias="q", min_length=1, max_length=500)],
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SearchService, Depends(get_search_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    source_type: Annotated[str | None, Query()] = None,
    topic_id: Annotated[int | None, Query(ge=1)] = None,
    project_id: Annotated[int | None, Query(ge=1)] = None,
    meeting_id: Annotated[int | None, Query(ge=1)] = None,
    document_id: Annotated[int | None, Query(ge=1)] = None,
    date_from: Annotated[datetime | None, Query()] = None,
    date_to: Annotated[datetime | None, Query()] = None,
) -> SearchListResponse:
    """Return owner-scoped lexical/vector results with source context."""

    items, total = await service.search(
        user.id,
        query,
        filters=SearchFilters(
            source_type=source_type,
            topic_id=topic_id,
            project_id=project_id,
            meeting_id=meeting_id,
            document_id=document_id,
            date_from=date_from,
            date_to=date_to,
        ),
        page=page,
        page_size=page_size,
    )
    return SearchListResponse(
        items=[
            SearchResultResponse(
                chunk_id=item.candidate.chunk_id,
                text=item.candidate.text,
                score=item.candidate.score,
                semantic_score=item.candidate.semantic_score,
                lexical_score=item.candidate.lexical_score,
                source_file_id=item.source_file_id,
                source_type=item.source_type,  # type: ignore[arg-type]
                source_title=item.source_title,
                document_id=item.document_id,
                meeting_id=item.meeting_id,
                location=item.location,
                source_offset_start=item.source_offset_start,
                source_offset_end=item.source_offset_end,
                source_start_ms=item.source_start_ms,
                source_end_ms=item.source_end_ms,
            )
            for item in items
        ],
        page=PageMetadata(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=(total + page_size - 1) // page_size if total else 0,
        ),
    )
