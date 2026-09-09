"""HTTP adapter for source-grounded knowledge views."""

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.auth.dependencies import get_current_user
from thoughtharbor.db.session import get_db
from thoughtharbor.domain.models import User
from thoughtharbor.knowledge.views import (
    ArtifactView,
    KnowledgeViewService,
)

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


class KnowledgeObjectResponse(BaseModel):
    id: int
    kind: Literal["topic", "project", "person", "organization", "custom"]
    title: str
    description: str | None
    metadata: dict[str, object]


class KnowledgeObjectListResponse(BaseModel):
    items: list[KnowledgeObjectResponse]
    page: dict[str, int]


class RenameRequest(BaseModel):
    title: str = Field(min_length=1, max_length=500)


class SourceContextResponse(BaseModel):
    chunk_id: int
    text: str
    location: dict[str, object]
    source_offset_start: int | None
    source_offset_end: int | None
    source_start_ms: int | None
    source_end_ms: int | None


class ArtifactResponse(BaseModel):
    id: int
    kind: str
    title: str | None
    content: str
    sources: list[SourceContextResponse]


class KnowledgeObjectDetailResponse(BaseModel):
    item: KnowledgeObjectResponse
    related: list[KnowledgeObjectResponse]
    artifacts: list[ArtifactResponse]


class DocumentDetailResponse(BaseModel):
    id: int
    title: str
    original_name: str
    media_type: str | None
    extracted_text: str | None
    metadata: dict[str, object]
    chunks: list[SourceContextResponse]
    artifacts: list[ArtifactResponse]


class TranscriptSegmentResponse(BaseModel):
    id: int
    sequence: int
    text: str
    start_ms: int
    end_ms: int
    speaker_label: str | None
    speaker_name: str | None


class MeetingDetailResponse(BaseModel):
    id: int
    title: str
    started_at: Any
    ended_at: Any
    metadata: dict[str, object]
    source_file_id: int | None
    segments: list[TranscriptSegmentResponse]
    artifacts: list[ArtifactResponse]


def get_service(session: Annotated[Session, Depends(get_db)]) -> KnowledgeViewService:
    return KnowledgeViewService(session)


@router.get(
    "/objects", response_model=KnowledgeObjectListResponse, summary="List knowledge objects"
)
def list_objects(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeViewService, Depends(get_service)],
    kind: Annotated[str | None, Query()] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
) -> KnowledgeObjectListResponse:
    items, total = service.list_objects(user.id, kind=kind, page=page, page_size=page_size)
    return KnowledgeObjectListResponse(
        items=[_object(item) for item in items],
        page={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size if total else 0,
        },
    )


@router.get(
    "/objects/{object_id}",
    response_model=KnowledgeObjectDetailResponse,
    summary="Get a knowledge object",
)
def get_object(
    object_id: int,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeViewService, Depends(get_service)],
) -> KnowledgeObjectDetailResponse:
    result = service.object(user.id, object_id)
    if result is None:
        raise ApplicationError(
            "KNOWLEDGE_NOT_FOUND", "The knowledge object does not exist.", status_code=404
        )
    return KnowledgeObjectDetailResponse(
        item=_object(result.item),
        related=[_object(item) for item in result.related],
        artifacts=[_artifact(item) for item in result.artifacts],
    )


@router.patch(
    "/objects/{object_id}",
    response_model=KnowledgeObjectResponse,
    summary="Rename a knowledge object",
)
def rename_object(
    object_id: int,
    payload: RenameRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeViewService, Depends(get_service)],
) -> KnowledgeObjectResponse:
    item = service.rename_object(user.id, object_id, payload.title)
    if item is None:
        raise ApplicationError(
            "KNOWLEDGE_NOT_FOUND", "The knowledge object does not exist.", status_code=404
        )
    return _object(item)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentDetailResponse,
    summary="Get a document knowledge view",
)
def get_document(
    document_id: int,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeViewService, Depends(get_service)],
) -> DocumentDetailResponse:
    result = service.document(user.id, document_id)
    if result is None:
        raise ApplicationError(
            "DOCUMENT_NOT_FOUND", "The document does not exist.", status_code=404
        )
    return DocumentDetailResponse(
        id=result.document.id,
        title=result.document.title,
        original_name=result.source.original_name,
        media_type=result.source.media_type,
        extracted_text=result.document.extracted_text,
        metadata=result.document.metadata_json,
        chunks=[_chunk(chunk) for chunk in result.chunks],
        artifacts=[_artifact(item) for item in result.artifacts],
    )


@router.get(
    "/meetings/{meeting_id}",
    response_model=MeetingDetailResponse,
    summary="Get a meeting knowledge view",
)
def get_meeting(
    meeting_id: int,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[KnowledgeViewService, Depends(get_service)],
) -> MeetingDetailResponse:
    result = service.meeting(user.id, meeting_id)
    if result is None:
        raise ApplicationError("MEETING_NOT_FOUND", "The meeting does not exist.", status_code=404)
    return MeetingDetailResponse(
        id=result.meeting.id,
        title=result.meeting.title,
        started_at=result.meeting.started_at,
        ended_at=result.meeting.ended_at,
        metadata=result.meeting.metadata_json,
        source_file_id=result.source.id if result.source else None,
        segments=[
            TranscriptSegmentResponse(
                id=item.segment.id,
                sequence=item.segment.sequence,
                text=item.segment.text,
                start_ms=item.segment.start_ms,
                end_ms=item.segment.end_ms,
                speaker_label=item.speaker.label if item.speaker else None,
                speaker_name=item.speaker.display_name if item.speaker else None,
            )
            for item in result.segments
        ],
        artifacts=[_artifact(item) for item in result.artifacts],
    )


def _object(item: Any) -> KnowledgeObjectResponse:
    return KnowledgeObjectResponse(
        id=item.id,
        kind=item.kind,
        title=item.title,
        description=item.description,
        metadata=item.metadata_json,
    )


def _chunk(item: Any) -> SourceContextResponse:
    return SourceContextResponse(
        chunk_id=item.id,
        text=item.text,
        location=item.location,
        source_offset_start=item.source_offset_start,
        source_offset_end=item.source_offset_end,
        source_start_ms=item.source_start_ms,
        source_end_ms=item.source_end_ms,
    )


def _artifact(item: ArtifactView) -> ArtifactResponse:
    return ArtifactResponse(
        id=item.artifact.id,
        kind=item.artifact.kind,
        title=item.artifact.title,
        content=item.artifact.content,
        sources=[_chunk(chunk) for chunk in item.sources],
    )
