"""HTTP delivery routes for owner-scoped meeting speakers."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from thoughtharbor.api.errors import ApplicationError
from thoughtharbor.api.schemas import ErrorResponse, SpeakerRenameRequest, SpeakerResponse
from thoughtharbor.auth.dependencies import get_current_user
from thoughtharbor.db.session import get_db
from thoughtharbor.domain.models import User
from thoughtharbor.meetings.service import SpeakerNotFoundError, SpeakerService

router = APIRouter(prefix="/meetings", tags=["meetings"])


def get_speaker_service(session: Annotated[Session, Depends(get_db)]) -> SpeakerService:
    """Build the application service for speaker operations."""

    return SpeakerService(session)


@router.get(
    "/{meeting_id}/speakers",
    response_model=list[SpeakerResponse],
    summary="List speakers for a meeting",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def list_speakers(
    meeting_id: int,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SpeakerService, Depends(get_speaker_service)],
) -> list[SpeakerResponse]:
    """Return anonymous or user-renamed speakers for an owned meeting."""

    try:
        speakers = service.list(owner_id=user.id, meeting_id=meeting_id)
    except SpeakerNotFoundError as error:
        raise ApplicationError("MEETING_NOT_FOUND", str(error), status_code=404) from error
    return [SpeakerResponse.model_validate(speaker) for speaker in speakers]


@router.patch(
    "/{meeting_id}/speakers/{speaker_id}",
    response_model=SpeakerResponse,
    summary="Rename a meeting speaker",
    responses={401: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def rename_speaker(
    meeting_id: int,
    speaker_id: int,
    payload: SpeakerRenameRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[SpeakerService, Depends(get_speaker_service)],
) -> SpeakerResponse:
    """Allow users to assign a human label without asserting identity automatically."""

    try:
        speaker = service.rename(
            owner_id=user.id,
            meeting_id=meeting_id,
            speaker_id=speaker_id,
            display_name=payload.display_name,
        )
    except SpeakerNotFoundError as error:
        raise ApplicationError("SPEAKER_NOT_FOUND", str(error), status_code=404) from error
    return SpeakerResponse.model_validate(speaker)
