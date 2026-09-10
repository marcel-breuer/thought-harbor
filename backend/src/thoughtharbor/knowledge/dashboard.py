"""Fast owner-scoped read model for the personal knowledge dashboard."""

from dataclasses import dataclass
from datetime import datetime
from typing import Literal, cast

from sqlalchemy import select
from sqlalchemy.orm import Session

from thoughtharbor.domain.models import (
    AIClassification,
    ClarificationRequest,
    Decision,
    DerivedArtifact,
    Document,
    KnowledgeObject,
    Meeting,
    OpenQuestion,
    ProcessingJob,
    SourceFile,
    Task,
)

DashboardActionType = Literal["task", "decision", "open_question"]
DashboardSourceType = Literal["document", "transcript", "email", "audio"]
DashboardKnowledgeKind = Literal["topic", "project", "person", "organization", "custom"]


@dataclass(frozen=True, slots=True)
class DashboardSource:
    id: int
    title: str
    source_type: DashboardSourceType
    ingestion_status: str
    created_at: datetime
    document_id: int | None
    meeting_id: int | None


@dataclass(frozen=True, slots=True)
class DashboardJob:
    id: int
    job_type: str
    status: str
    subject_type: str | None
    subject_id: int | None
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class DashboardClarification:
    id: int
    question: str
    label: str
    confidence: float
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DashboardAction:
    id: int
    item_type: DashboardActionType
    title: str | None
    content: str
    status: str
    created_at: datetime


@dataclass(frozen=True, slots=True)
class DashboardTopic:
    id: int
    kind: DashboardKnowledgeKind
    title: str


@dataclass(frozen=True, slots=True)
class DashboardView:
    recent_sources: tuple[DashboardSource, ...]
    processing_attention: tuple[DashboardJob, ...]
    pending_clarifications: tuple[DashboardClarification, ...]
    open_tasks: tuple[DashboardAction, ...]
    open_questions: tuple[DashboardAction, ...]
    recent_decisions: tuple[DashboardAction, ...]
    active_topics: tuple[DashboardTopic, ...]
    insights: tuple[object, ...]


class DashboardService:
    """Aggregate cheap persisted read models for the authenticated dashboard."""

    def __init__(self, session: Session, *, limit: int = 6) -> None:
        self.session = session
        self.limit = limit

    def get(self, owner_id: int) -> DashboardView:
        """Build the dashboard from bounded queries; AI generation is never synchronous."""

        sources = tuple(
            self.session.scalars(
                select(SourceFile)
                .where(SourceFile.owner_id == owner_id, SourceFile.deleted_at.is_(None))
                .order_by(SourceFile.created_at.desc())
                .limit(self.limit)
            )
        )
        documents = {
            item.source_file_id: item.id
            for item in self.session.scalars(
                select(Document).where(Document.owner_id == owner_id, Document.deleted_at.is_(None))
            )
        }
        meetings = {
            item.source_file_id: item.id
            for item in self.session.scalars(
                select(Meeting).where(Meeting.owner_id == owner_id, Meeting.deleted_at.is_(None))
            )
        }
        recent_sources = tuple(
            DashboardSource(
                id=item.id,
                title=item.original_name,
                source_type=self._source_type(item.metadata_json.get("source_type")),
                ingestion_status=item.ingestion_status,
                created_at=item.created_at,
                document_id=documents.get(item.id),
                meeting_id=meetings.get(item.id),
            )
            for item in sources
        )

        jobs = tuple(
            self.session.scalars(
                select(ProcessingJob)
                .where(
                    ProcessingJob.owner_id == owner_id,
                    ProcessingJob.status.in_(("queued", "running", "failed", "needs_input")),
                )
                .order_by(ProcessingJob.updated_at.desc())
                .limit(self.limit)
            )
        )
        processing_attention = tuple(
            DashboardJob(
                id=job.id,
                job_type=job.job_type,
                status=job.status,
                subject_type=job.subject_type,
                subject_id=job.subject_id,
                updated_at=job.updated_at,
            )
            for job in jobs
        )

        clarification_rows = self.session.execute(
            select(ClarificationRequest, AIClassification)
            .join(AIClassification, AIClassification.id == ClarificationRequest.classification_id)
            .where(
                ClarificationRequest.owner_id == owner_id,
                ClarificationRequest.status == "open",
                ClarificationRequest.deleted_at.is_(None),
                AIClassification.deleted_at.is_(None),
            )
            .order_by(ClarificationRequest.created_at)
            .limit(self.limit)
        )
        pending_clarifications = tuple(
            DashboardClarification(
                id=request.id,
                question=request.question,
                label=classification.label,
                confidence=classification.confidence,
                created_at=request.created_at,
            )
            for request, classification in clarification_rows
        )

        action_artifacts = tuple(
            self.session.scalars(
                select(DerivedArtifact)
                .where(
                    DerivedArtifact.owner_id == owner_id,
                    DerivedArtifact.deleted_at.is_(None),
                    DerivedArtifact.kind.in_(("task", "decision", "open_question")),
                    DerivedArtifact.metadata_json["active"].as_boolean().is_not(False),
                )
                .order_by(DerivedArtifact.created_at.desc())
            )
        )
        action_lists: dict[str, list[DashboardAction]] = {
            "task": [],
            "decision": [],
            "open_question": [],
        }
        for artifact in action_artifacts:
            item_type = cast(DashboardActionType, artifact.kind)
            record = self._action_record(item_type, artifact.id)
            if record is None:
                continue
            if item_type == "task" and record.status not in {"open", "in_progress"}:
                continue
            if item_type == "open_question" and record.status != "open":
                continue
            action_lists[item_type].append(
                DashboardAction(
                    id=artifact.id,
                    item_type=item_type,
                    title=artifact.title,
                    content=artifact.content,
                    status=record.status,
                    created_at=artifact.created_at,
                )
            )

        topics = tuple(
            self.session.scalars(
                select(KnowledgeObject)
                .where(
                    KnowledgeObject.owner_id == owner_id,
                    KnowledgeObject.deleted_at.is_(None),
                    KnowledgeObject.kind.in_(("topic", "project")),
                )
                .order_by(KnowledgeObject.updated_at.desc(), KnowledgeObject.title)
                .limit(self.limit)
            )
        )
        return DashboardView(
            recent_sources=recent_sources,
            processing_attention=processing_attention,
            pending_clarifications=pending_clarifications,
            open_tasks=tuple(action_lists["task"][: self.limit]),
            open_questions=tuple(action_lists["open_question"][: self.limit]),
            recent_decisions=tuple(action_lists["decision"][: self.limit]),
            active_topics=tuple(
                DashboardTopic(item.id, cast(DashboardKnowledgeKind, item.kind), item.title)
                for item in topics
            ),
            insights=(),
        )

    @staticmethod
    def _source_type(value: object) -> DashboardSourceType:
        return cast(
            DashboardSourceType,
            value if value in {"document", "transcript", "email", "audio"} else "document",
        )

    def _action_record(
        self, item_type: DashboardActionType, artifact_id: int
    ) -> Task | Decision | OpenQuestion | None:
        if item_type == "task":
            return self.session.scalar(select(Task).where(Task.artifact_id == artifact_id))
        if item_type == "decision":
            return self.session.scalar(select(Decision).where(Decision.artifact_id == artifact_id))
        return self.session.scalar(
            select(OpenQuestion).where(OpenQuestion.artifact_id == artifact_id)
        )
