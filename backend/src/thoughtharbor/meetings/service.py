"""Application services for meeting speaker management."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from thoughtharbor.domain.models import Meeting, Speaker


class SpeakerNotFoundError(Exception):
    """Raised when a speaker is not owned by the requested meeting owner."""


class SpeakerService:
    """Keep speaker identity assignment user-controlled and owner-scoped."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(self, *, owner_id: int, meeting_id: int) -> list[Speaker]:
        """List only speakers belonging to the owner's meeting."""

        meeting = self._meeting(owner_id=owner_id, meeting_id=meeting_id)
        if meeting is None:
            raise SpeakerNotFoundError("The meeting does not exist")
        return list(
            self.session.scalars(
                select(Speaker).where(Speaker.meeting_id == meeting.id).order_by(Speaker.id)
            )
        )

    def rename(
        self, *, owner_id: int, meeting_id: int, speaker_id: int, display_name: str
    ) -> Speaker:
        """Set a human label without changing the anonymous source label."""

        speaker = self.session.scalar(
            select(Speaker)
            .join(Meeting, Speaker.meeting_id == Meeting.id)
            .where(
                Speaker.id == speaker_id,
                Speaker.meeting_id == meeting_id,
                Meeting.owner_id == owner_id,
                Meeting.deleted_at.is_(None),
            )
        )
        if speaker is None:
            raise SpeakerNotFoundError("The speaker does not exist")
        speaker.display_name = display_name.strip()
        self.session.commit()
        self.session.refresh(speaker)
        return speaker

    def _meeting(self, *, owner_id: int, meeting_id: int) -> Meeting | None:
        return self.session.scalar(
            select(Meeting).where(
                Meeting.id == meeting_id,
                Meeting.owner_id == owner_id,
                Meeting.deleted_at.is_(None),
            )
        )
