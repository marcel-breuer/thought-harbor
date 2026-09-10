"""HTTP adapter for grounded RAG chat."""

from datetime import datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from thoughtharbor.api.middleware import rate_limit_dependency
from thoughtharbor.api.schemas import ErrorResponse
from thoughtharbor.auth.dependencies import get_current_user
from thoughtharbor.chat.service import RAGService
from thoughtharbor.db.session import get_db
from thoughtharbor.domain.models import User
from thoughtharbor.search.service import SearchFilters

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequestBody(BaseModel):
    """Question and optional owner-scoped conversation/filter context."""

    question: str = Field(min_length=1, max_length=10_000)
    conversation_id: int | None = Field(default=None, ge=1)
    source_type: Literal["document", "transcript", "email", "audio"] | None = None
    topic_id: int | None = Field(default=None, ge=1)
    project_id: int | None = Field(default=None, ge=1)
    meeting_id: int | None = Field(default=None, ge=1)
    document_id: int | None = Field(default=None, ge=1)
    date_from: datetime | None = None
    date_to: datetime | None = None


class CitationResponse(BaseModel):
    """Exact source context attached by the server."""

    marker: str
    chunk_id: int
    source_file_id: int
    source_type: str
    source_title: str | None
    excerpt: str
    location: dict[str, object]
    source_offset_start: int | None
    source_offset_end: int | None
    source_start_ms: int | None
    source_end_ms: int | None


class ChatResponse(BaseModel):
    """Grounded answer with server-derived citations."""

    conversation_id: int
    message_id: int
    answer: str
    evidence_sufficient: bool
    citations: list[CitationResponse]


def get_rag_service(
    session: Annotated[Session, Depends(get_db)],
) -> RAGService:
    return RAGService(session)


@router.post(
    "",
    response_model=ChatResponse,
    summary="Ask the grounded knowledge assistant",
    responses={401: {"model": ErrorResponse, "description": "Authentication is required."}},
    dependencies=[Depends(rate_limit_dependency("ai"))],
)
async def ask(
    payload: ChatRequestBody,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RAGService, Depends(get_rag_service)],
) -> ChatResponse:
    result = await service.ask(
        user.id,
        payload.question,
        conversation_id=payload.conversation_id,
        filters=SearchFilters(
            source_type=payload.source_type,
            topic_id=payload.topic_id,
            project_id=payload.project_id,
            meeting_id=payload.meeting_id,
            document_id=payload.document_id,
            date_from=payload.date_from,
            date_to=payload.date_to,
        ),
    )
    return ChatResponse(
        conversation_id=result.conversation_id,
        message_id=result.message_id,
        answer=result.answer,
        evidence_sufficient=result.evidence_sufficient,
        citations=[CitationResponse(**citation.as_dict()) for citation in result.citations],
    )
