"""Owner-scoped application service for action-oriented knowledge."""

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from thoughtharbor.domain.models import (
    AIClassification,
    ArtifactSource,
    ContentChunk,
    Decision,
    DerivedArtifact,
    Document,
    KnowledgeObject,
    Meeting,
    OpenQuestion,
    SourceFile,
    Task,
    Transcript,
    TranscriptSegment,
    User,
)

ActionItemType = Literal["task", "decision", "open_question"]
SourceType = Literal["document", "transcript", "email", "audio"]
KnowledgeKind = Literal["topic", "project", "person", "organization", "custom"]

TASK_STATUSES = frozenset({"open", "in_progress", "done", "dismissed"})
DECISION_STATUSES = frozenset({"active", "superseded", "retracted"})
QUESTION_STATUSES = frozenset({"open", "resolved", "dismissed"})


@dataclass(frozen=True, slots=True)
class ActionTopicView:
    id: int
    kind: KnowledgeKind
    title: str


@dataclass(frozen=True, slots=True)
class ActionSourceView:
    id: int
    source_type: SourceType
    title: str
    source_file_id: int | None
    chunk: ContentChunk


@dataclass(frozen=True, slots=True)
class ActionStatusView:
    status: str
    changed_at: datetime
    previous_status: str | None


@dataclass(frozen=True, slots=True)
class ActionItemView:
    artifact: DerivedArtifact
    item_type: ActionItemType
    status: str
    assignee: User | None
    due_at: datetime | None
    topics: tuple[ActionTopicView, ...]
    sources: tuple[ActionSourceView, ...]
    status_history: tuple[ActionStatusView, ...]


@dataclass(frozen=True, slots=True)
class ActionSummaryView:
    open_tasks: int
    recent_decisions: int
    open_questions: int


class ActionItemError(Exception):
    """Expected action-item application failure."""


class ActionItemNotFoundError(ActionItemError):
    """The action item is absent or not owned by the current user."""


class InvalidActionItemStatusError(ActionItemError):
    """A status is not valid for the selected action-item type."""


class ActionItemService:
    """Query and update canonical tasks, decisions, and open questions."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        owner_id: int,
        *,
        item_type: ActionItemType | None,
        status: str | None,
        topic_id: int | None,
        project_id: int | None,
        source_type: SourceType | None,
        assignee_user_id: int | None,
        date_from: date | None,
        date_to: date | None,
        page: int,
        page_size: int,
    ) -> tuple[tuple[ActionItemView, ...], int]:
        """Return filtered, paginated action items without exposing other owners."""

        statement = select(DerivedArtifact).where(
            DerivedArtifact.owner_id == owner_id,
            DerivedArtifact.deleted_at.is_(None),
            DerivedArtifact.kind.in_(("task", "decision", "open_question")),
            DerivedArtifact.metadata_json["active"].as_boolean().is_not(False),
        )
        if item_type is not None:
            statement = statement.where(DerivedArtifact.kind == item_type)
        artifacts = tuple(
            self.session.scalars(statement.order_by(DerivedArtifact.created_at.desc()))
        )

        filtered: list[ActionItemView] = []
        for artifact in artifacts:
            item = self._build(owner_id, artifact)
            if status is not None and item.status != status:
                continue
            if assignee_user_id is not None and (
                item.assignee is None or item.assignee.id != assignee_user_id
            ):
                continue
            if topic_id is not None and not any(topic.id == topic_id for topic in item.topics):
                continue
            if project_id is not None and not any(
                topic.id == project_id and topic.kind == "project" for topic in item.topics
            ):
                continue
            if source_type is not None and not any(
                source.source_type == source_type for source in item.sources
            ):
                continue
            created = artifact.created_at
            if date_from is not None and (created is None or created.date() < date_from):
                continue
            if date_to is not None and (created is None or created.date() > date_to):
                continue
            filtered.append(item)

        start = (page - 1) * page_size
        return tuple(filtered[start : start + page_size]), len(filtered)

    def get(self, owner_id: int, artifact_id: int) -> ActionItemView:
        """Return one owner-scoped action item or raise a stable not-found error."""

        artifact = self.session.scalar(
            select(DerivedArtifact).where(
                DerivedArtifact.id == artifact_id,
                DerivedArtifact.owner_id == owner_id,
                DerivedArtifact.deleted_at.is_(None),
                DerivedArtifact.kind.in_(("task", "decision", "open_question")),
                DerivedArtifact.metadata_json["active"].as_boolean().is_not(False),
            )
        )
        if artifact is None:
            raise ActionItemNotFoundError("The action item does not exist")
        return self._build(owner_id, artifact)

    def summary(self, owner_id: int) -> ActionSummaryView:
        """Return compact counts for the action-knowledge header."""

        statement = select(DerivedArtifact).where(
            DerivedArtifact.owner_id == owner_id,
            DerivedArtifact.deleted_at.is_(None),
            DerivedArtifact.kind.in_(("task", "decision", "open_question")),
            DerivedArtifact.metadata_json["active"].as_boolean().is_not(False),
        )
        open_tasks = recent_decisions = open_questions = 0
        for artifact in self.session.scalars(statement):
            item = self._build(owner_id, artifact)
            if item.item_type == "task" and item.status in {"open", "in_progress"}:
                open_tasks += 1
            elif item.item_type == "decision":
                recent_decisions += 1
            elif item.item_type == "open_question" and item.status == "open":
                open_questions += 1
        return ActionSummaryView(open_tasks, recent_decisions, open_questions)

    def update_status(self, owner_id: int, artifact_id: int, status: str) -> ActionItemView:
        """Update a specialized record while retaining a durable status history."""

        item = self.get(owner_id, artifact_id)
        allowed = self._allowed_statuses(item.item_type)
        if status not in allowed:
            allowed_values = ", ".join(sorted(allowed))
            raise InvalidActionItemStatusError(
                f"Status '{status}' is not valid for {item.item_type}; use {allowed_values}"
            )

        if status != item.status:
            specialized = self._specialized(item.artifact, item.item_type)
            specialized.status = status
            now = datetime.now(UTC)
            history = list(item.artifact.metadata_json.get("status_history", []))
            history.append(
                {
                    "status": status,
                    "previous_status": item.status,
                    "changed_at": now.isoformat(),
                }
            )
            item.artifact.metadata_json = {**item.artifact.metadata_json, "status_history": history}
            self.session.commit()
        return self.get(owner_id, artifact_id)

    def _build(self, owner_id: int, artifact: DerivedArtifact) -> ActionItemView:
        item_type = cast(ActionItemType, artifact.kind)
        specialized = self._specialized(artifact, item_type)
        assignee = None
        due_at = None
        if isinstance(specialized, Task):
            due_at = specialized.due_at
            if specialized.assignee_user_id is not None:
                assignee = self.session.scalar(
                    select(User).where(
                        User.id == specialized.assignee_user_id,
                        User.id == owner_id,
                    )
                )
        return ActionItemView(
            artifact=artifact,
            item_type=item_type,
            status=specialized.status,
            assignee=assignee,
            due_at=due_at,
            topics=self._topics_for_artifact(owner_id, artifact.id),
            sources=self._sources_for_artifact(owner_id, artifact.id),
            status_history=self._status_history(artifact),
        )

    def _specialized(
        self, artifact: DerivedArtifact, item_type: ActionItemType
    ) -> Task | Decision | OpenQuestion:
        model: type[Task] | type[Decision] | type[OpenQuestion]
        if item_type == "task":
            model = Task
        elif item_type == "decision":
            model = Decision
        else:
            model = OpenQuestion
        result = self.session.scalar(select(model).where(model.artifact_id == artifact.id))
        if result is None:
            raise ActionItemError("The action item record is incomplete")
        return cast(Task | Decision | OpenQuestion, result)

    def _topics_for_artifact(self, owner_id: int, artifact_id: int) -> tuple[ActionTopicView, ...]:
        statement = (
            select(KnowledgeObject)
            .join(AIClassification, AIClassification.knowledge_object_id == KnowledgeObject.id)
            .join(ContentChunk, ContentChunk.id == AIClassification.content_chunk_id)
            .join(ArtifactSource, ArtifactSource.content_chunk_id == ContentChunk.id)
            .where(
                KnowledgeObject.owner_id == owner_id,
                KnowledgeObject.deleted_at.is_(None),
                AIClassification.owner_id == owner_id,
                AIClassification.deleted_at.is_(None),
                ArtifactSource.artifact_id == artifact_id,
            )
            .distinct()
            .order_by(KnowledgeObject.title)
        )
        return tuple(
            ActionTopicView(item.id, cast(KnowledgeKind, item.kind), item.title)
            for item in self.session.scalars(statement)
        )

    def _sources_for_artifact(
        self, owner_id: int, artifact_id: int
    ) -> tuple[ActionSourceView, ...]:
        chunks = tuple(
            self.session.scalars(
                select(ContentChunk)
                .join(ArtifactSource, ArtifactSource.content_chunk_id == ContentChunk.id)
                .where(
                    ArtifactSource.artifact_id == artifact_id,
                    ContentChunk.owner_id == owner_id,
                    ContentChunk.deleted_at.is_(None),
                )
                .order_by(ContentChunk.sequence)
            )
        )
        sources: list[ActionSourceView] = []
        for chunk in chunks:
            if chunk.document_id is not None:
                document = self.session.scalar(
                    select(Document).where(
                        Document.id == chunk.document_id,
                        Document.owner_id == owner_id,
                        Document.deleted_at.is_(None),
                    )
                )
                if document is None:
                    continue
                source_file = self.session.scalar(
                    select(SourceFile).where(
                        SourceFile.id == document.source_file_id,
                        SourceFile.owner_id == owner_id,
                        SourceFile.deleted_at.is_(None),
                    )
                )
                if source_file is None:
                    continue
                source_kind = source_file.metadata_json.get("source_type", "document")
                source_type = (
                    source_kind
                    if source_kind in {"document", "transcript", "email", "audio"}
                    else "document"
                )
                sources.append(
                    ActionSourceView(
                        document.id,
                        cast(SourceType, source_type),
                        document.title,
                        source_file.id,
                        chunk,
                    )
                )
                continue

            if chunk.transcript_segment_id is None:
                continue
            segment = self.session.scalar(
                select(TranscriptSegment).where(TranscriptSegment.id == chunk.transcript_segment_id)
            )
            if segment is None:
                continue
            transcript = self.session.scalar(
                select(Transcript).where(Transcript.id == segment.transcript_id)
            )
            meeting = (
                self.session.scalar(
                    select(Meeting).where(
                        Meeting.id == transcript.meeting_id, Meeting.owner_id == owner_id
                    )
                )
                if transcript is not None
                else None
            )
            if meeting is None:
                continue
            source_file = (
                self.session.scalar(
                    select(SourceFile).where(
                        SourceFile.id == meeting.source_file_id,
                        SourceFile.owner_id == owner_id,
                        SourceFile.deleted_at.is_(None),
                    )
                )
                if meeting.source_file_id is not None
                else None
            )
            source_kind = (
                source_file.metadata_json.get("source_type", "audio") if source_file else "audio"
            )
            source_type = (
                source_kind
                if source_kind in {"document", "transcript", "email", "audio"}
                else "audio"
            )
            sources.append(
                ActionSourceView(
                    meeting.id,
                    cast(SourceType, source_type),
                    meeting.title,
                    source_file.id if source_file else None,
                    chunk,
                )
            )
        return tuple(sources)

    @staticmethod
    def _allowed_statuses(item_type: ActionItemType) -> frozenset[str]:
        if item_type == "task":
            return TASK_STATUSES
        if item_type == "decision":
            return DECISION_STATUSES
        return QUESTION_STATUSES

    @staticmethod
    def _status_history(artifact: DerivedArtifact) -> tuple[ActionStatusView, ...]:
        values = artifact.metadata_json.get("status_history", [])
        history: list[ActionStatusView] = []
        for value in values:
            if not isinstance(value, dict) or not isinstance(value.get("changed_at"), str):
                continue
            try:
                changed_at = datetime.fromisoformat(value["changed_at"])
            except ValueError:
                continue
            history.append(
                ActionStatusView(
                    status=str(value.get("status", "")),
                    changed_at=changed_at,
                    previous_status=(
                        str(value["previous_status"])
                        if value.get("previous_status") is not None
                        else None
                    ),
                )
            )
        return tuple(history)
