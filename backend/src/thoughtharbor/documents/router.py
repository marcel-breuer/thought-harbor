"""HTTP delivery routes for the authenticated ingestion inbox."""

from datetime import datetime
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, File, Header, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.api.middleware import rate_limit_dependency
from thoughtharbor.api.schemas import (
    ErrorResponse,
    InboxItemResponse,
    InboxListResponse,
    IngestionStatusEvent,
    PageMetadata,
)
from thoughtharbor.auth.dependencies import get_current_user
from thoughtharbor.db.session import get_db
from thoughtharbor.documents.ingestion import (
    INGESTION_STATUSES,
    IngestionError,
    IngestionNotFoundError,
    IngestionService,
    IngestionStatus,
    UnsupportedSourceTypeError,
)
from thoughtharbor.domain.models import Document, Meeting, SourceFile, User
from thoughtharbor.storage.factory import get_storage
from thoughtharbor.storage.service import StorageValidationError

router = APIRouter(prefix="/inbox", tags=["inbox"])
PRIVATE_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse, "description": "Authentication is required."},
    404: {"model": ErrorResponse, "description": "The source file does not exist."},
    422: {"model": ErrorResponse, "description": "The upload or filter is invalid."},
}


def get_ingestion_service(
    session: Annotated[Session, Depends(get_db)],
) -> IngestionService:
    """Build the application service with the configured storage port."""

    return IngestionService(session, get_storage())


@router.post(
    "/upload",
    response_model=InboxItemResponse,
    status_code=201,
    summary="Upload a source file to the inbox",
    responses={
        **PRIVATE_RESPONSES,
        400: {"model": ErrorResponse, "description": "Upload rejected."},
    },
    dependencies=[Depends(rate_limit_dependency("upload"))],
)
def upload(
    file: Annotated[UploadFile, File(description="Document, transcript, email, or audio file.")],
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> InboxItemResponse:
    """Stream an authenticated upload into local storage and queue ingestion."""

    try:
        item = service.upload(
            owner_id=user.id,
            original_name=file.filename or "",
            media_type=file.content_type,
            source=file.file,
            idempotency_key=idempotency_key,
        )
    except UnsupportedSourceTypeError as error:
        raise ApplicationError("UPLOAD_UNSUPPORTED_TYPE", str(error), status_code=415) from error
    except StorageValidationError as error:
        raise ApplicationError("UPLOAD_INVALID", str(error), status_code=413) from error
    return _response_for(item, service.session)


@router.get(
    "",
    response_model=InboxListResponse,
    summary="List the authenticated user's inbox",
    responses=PRIVATE_RESPONSES,
)
def list_inbox(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    status: Annotated[str | None, Query()] = None,
    source_type: Annotated[str | None, Query()] = None,
) -> InboxListResponse:
    """Return filterable inbox items without exposing other users' records."""

    if status is not None and status not in INGESTION_STATUSES:
        raise ApplicationError("INVALID_STATUS", "Unsupported ingestion status.")
    if source_type is not None and source_type not in {"document", "transcript", "email", "audio"}:
        raise ApplicationError("INVALID_SOURCE_TYPE", "Unsupported source type.")
    result = service.list(
        owner_id=user.id,
        page=page,
        page_size=page_size,
        status=status,
        source_type=source_type,
    )
    total_pages = (result.total + page_size - 1) // page_size if result.total else 0
    return InboxListResponse(
        items=[_response_for(item, service.session) for item in result.items],
        page=PageMetadata(
            page=page, page_size=page_size, total=result.total, total_pages=total_pages
        ),
    )


@router.get(
    "/{source_file_id}",
    response_model=InboxItemResponse,
    summary="Get one inbox item",
    responses=PRIVATE_RESPONSES,
)
def get_item(
    source_file_id: int,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> InboxItemResponse:
    """Return one source file and any currently linked result records."""

    try:
        item = service.get(owner_id=user.id, source_file_id=source_file_id)
    except IngestionError as error:
        raise ApplicationError("INBOX_NOT_FOUND", str(error), status_code=404) from error
    return _response_for(item, service.session)


@router.post(
    "/{source_file_id}/retry",
    response_model=InboxItemResponse,
    summary="Retry failed inbox processing",
    responses={
        **PRIVATE_RESPONSES,
        400: {"model": ErrorResponse, "description": "Retry rejected."},
    },
)
def retry(
    source_file_id: int,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[IngestionService, Depends(get_ingestion_service)],
) -> InboxItemResponse:
    """Requeue a failed item while retaining its status timeline."""

    try:
        item = service.retry(owner_id=user.id, source_file_id=source_file_id)
    except IngestionError as error:
        status_code = 404 if isinstance(error, IngestionNotFoundError) else 400
        raise ApplicationError(
            "INBOX_RETRY_REJECTED", str(error), status_code=status_code
        ) from error
    return _response_for(item, service.session)


def _response_for(item: SourceFile, session: Session) -> InboxItemResponse:
    metadata = item.metadata_json
    events = [
        IngestionStatusEvent(
            status=cast(IngestionStatus, event["status"]), at=datetime.fromisoformat(event["at"])
        )
        for event in cast(list[dict[str, str]], metadata.get("status_timeline", []))
    ]
    document_id = session.scalar(select(Document.id).where(Document.source_file_id == item.id))
    meeting_id = session.scalar(select(Meeting.id).where(Meeting.source_file_id == item.id))
    return InboxItemResponse(
        id=item.id,
        original_name=item.original_name,
        media_type=item.media_type,
        byte_size=item.byte_size,
        sha256=item.sha256,
        source_type=cast(Any, metadata.get("source_type", "document")),
        ingestion_status=cast(Any, item.ingestion_status),
        status_timeline=events,
        progress=cast(float | None, metadata.get("progress")),
        error_message=cast(str | None, metadata.get("error")),
        created_at=item.created_at,
        updated_at=item.updated_at,
        document_id=document_id,
        meeting_id=meeting_id,
    )
