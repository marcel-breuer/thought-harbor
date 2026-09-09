"""Owner-scoped read models for human-readable knowledge views."""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from thoughtharbor.domain.models import (
    AIClassification,
    ArtifactSource,
    ContentChunk,
    DerivedArtifact,
    Document,
    KnowledgeObject,
    KnowledgeRelation,
    Meeting,
    SourceFile,
    Speaker,
    Transcript,
    TranscriptSegment,
)


@dataclass(frozen=True, slots=True)
class ArtifactView:
    artifact: DerivedArtifact
    sources: tuple[ContentChunk, ...]


@dataclass(frozen=True, slots=True)
class KnowledgeObjectView:
    item: KnowledgeObject
    related: tuple[KnowledgeObject, ...]
    artifacts: tuple[ArtifactView, ...]


@dataclass(frozen=True, slots=True)
class DocumentView:
    document: Document
    source: SourceFile
    chunks: tuple[ContentChunk, ...]
    artifacts: tuple[ArtifactView, ...]


@dataclass(frozen=True, slots=True)
class TranscriptSegmentView:
    segment: TranscriptSegment
    speaker: Speaker | None


@dataclass(frozen=True, slots=True)
class MeetingView:
    meeting: Meeting
    source: SourceFile | None
    segments: tuple[TranscriptSegmentView, ...]
    artifacts: tuple[ArtifactView, ...]


class KnowledgeViewService:
    """Build owner-scoped views without leaking persistence into UI adapters."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_objects(
        self, owner_id: int, *, kind: str | None, page: int, page_size: int
    ) -> tuple[tuple[KnowledgeObject, ...], int]:
        statement = select(KnowledgeObject).where(
            KnowledgeObject.owner_id == owner_id,
            KnowledgeObject.deleted_at.is_(None),
        )
        if kind:
            statement = statement.where(KnowledgeObject.kind == kind)
        all_items = tuple(self.session.scalars(statement.order_by(KnowledgeObject.title)))
        start = (page - 1) * page_size
        return all_items[start : start + page_size], len(all_items)

    def object(self, owner_id: int, object_id: int) -> KnowledgeObjectView | None:
        item = self.session.scalar(
            select(KnowledgeObject).where(
                KnowledgeObject.id == object_id,
                KnowledgeObject.owner_id == owner_id,
                KnowledgeObject.deleted_at.is_(None),
            )
        )
        if item is None:
            return None
        relation_rows = tuple(
            self.session.execute(
                select(
                    KnowledgeRelation.source_object_id,
                    KnowledgeRelation.target_object_id,
                ).where(
                    KnowledgeRelation.owner_id == owner_id,
                    (KnowledgeRelation.source_object_id == object_id)
                    | (KnowledgeRelation.target_object_id == object_id),
                )
            )
        )
        relation_ids = tuple(
            related_id for row in relation_rows for related_id in row if related_id != object_id
        )
        related = (
            tuple(
                self.session.scalars(
                    select(KnowledgeObject).where(
                        KnowledgeObject.owner_id == owner_id,
                        KnowledgeObject.id.in_(relation_ids),
                        KnowledgeObject.deleted_at.is_(None),
                    )
                )
            )
            if relation_ids
            else ()
        )
        chunk_ids = tuple(
            self.session.scalars(
                select(ContentChunk.id)
                .join(ArtifactSource, ArtifactSource.content_chunk_id == ContentChunk.id)
                .join(DerivedArtifact, DerivedArtifact.id == ArtifactSource.artifact_id)
                .join(AIClassification, AIClassification.artifact_id == DerivedArtifact.id)
                .where(
                    DerivedArtifact.owner_id == owner_id,
                    DerivedArtifact.deleted_at.is_(None),
                    ContentChunk.deleted_at.is_(None),
                    AIClassification.owner_id == owner_id,
                    AIClassification.knowledge_object_id == object_id,
                    AIClassification.deleted_at.is_(None),
                )
            )
        )
        artifacts = self._artifacts_for_chunks(owner_id, chunk_ids)
        return KnowledgeObjectView(item=item, related=related, artifacts=artifacts)

    def document(self, owner_id: int, document_id: int) -> DocumentView | None:
        row = self.session.execute(
            select(Document, SourceFile)
            .join(SourceFile, SourceFile.id == Document.source_file_id)
            .where(
                Document.id == document_id,
                Document.owner_id == owner_id,
                Document.deleted_at.is_(None),
                SourceFile.deleted_at.is_(None),
            )
        ).first()
        if row is None:
            return None
        document, source = row
        chunks = tuple(
            self.session.scalars(
                select(ContentChunk)
                .where(
                    ContentChunk.document_id == document_id,
                    ContentChunk.deleted_at.is_(None),
                )
                .order_by(ContentChunk.sequence)
            )
        )
        artifacts = self._artifacts_for_chunks(owner_id, tuple(chunk.id for chunk in chunks))
        return DocumentView(document, source, chunks, artifacts)

    def meeting(self, owner_id: int, meeting_id: int) -> MeetingView | None:
        meeting = self.session.scalar(
            select(Meeting).where(
                Meeting.id == meeting_id,
                Meeting.owner_id == owner_id,
                Meeting.deleted_at.is_(None),
            )
        )
        if meeting is None:
            return None
        source = (
            self.session.scalar(select(SourceFile).where(SourceFile.id == meeting.source_file_id))
            if meeting.source_file_id is not None
            else None
        )
        transcript = self.session.scalar(
            select(Transcript).where(Transcript.meeting_id == meeting_id)
        )
        segments: tuple[TranscriptSegmentView, ...] = ()
        if transcript is not None:
            rows = self.session.execute(
                select(TranscriptSegment, Speaker)
                .outerjoin(Speaker, Speaker.id == TranscriptSegment.speaker_id)
                .where(TranscriptSegment.transcript_id == transcript.id)
                .order_by(TranscriptSegment.sequence)
            )
            segments = tuple(TranscriptSegmentView(segment, speaker) for segment, speaker in rows)
        chunk_ids = tuple(
            self.session.scalars(
                select(ContentChunk.id)
                .join(TranscriptSegment, TranscriptSegment.id == ContentChunk.transcript_segment_id)
                .join(Transcript, Transcript.id == TranscriptSegment.transcript_id)
                .where(Transcript.meeting_id == meeting_id, ContentChunk.deleted_at.is_(None))
            )
        )
        return MeetingView(
            meeting, source, segments, self._artifacts_for_chunks(owner_id, chunk_ids)
        )

    def rename_object(self, owner_id: int, object_id: int, title: str) -> KnowledgeObject | None:
        item = self.session.scalar(
            select(KnowledgeObject).where(
                KnowledgeObject.id == object_id,
                KnowledgeObject.owner_id == owner_id,
                KnowledgeObject.deleted_at.is_(None),
            )
        )
        if item is None:
            return None
        item.title = title.strip()
        self.session.commit()
        self.session.refresh(item)
        return item

    def _artifacts_for_chunks(
        self, owner_id: int, chunk_ids: tuple[int, ...]
    ) -> tuple[ArtifactView, ...]:
        if not chunk_ids:
            return ()
        artifacts = tuple(
            self.session.scalars(
                select(DerivedArtifact)
                .join(ArtifactSource, ArtifactSource.artifact_id == DerivedArtifact.id)
                .where(
                    ArtifactSource.content_chunk_id.in_(chunk_ids),
                    DerivedArtifact.owner_id == owner_id,
                    DerivedArtifact.deleted_at.is_(None),
                )
                .distinct()
                .order_by(DerivedArtifact.created_at.desc())
            )
        )
        return tuple(
            ArtifactView(
                artifact,
                tuple(
                    self.session.scalars(
                        select(ContentChunk)
                        .join(ArtifactSource, ArtifactSource.content_chunk_id == ContentChunk.id)
                        .where(
                            ArtifactSource.artifact_id == artifact.id,
                            ContentChunk.deleted_at.is_(None),
                        )
                    )
                ),
            )
            for artifact in artifacts
        )
