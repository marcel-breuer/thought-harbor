"""Confidence-based classification review and human resolution services."""

import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from thoughtharbor.domain.models import (
    AIClassification,
    ClarificationRequest,
    ContentChunk,
    DerivedArtifact,
    KnowledgeObject,
    ProcessingJob,
    SourceFile,
)

ClarificationAction = Literal["accept", "reject", "edit", "assign"]


@dataclass(frozen=True, slots=True)
class ClarificationSettings:
    """Thresholds controlling automatic acceptance and human review."""

    auto_accept_threshold: float = 0.85

    @classmethod
    def from_environment(cls) -> "ClarificationSettings":
        value = float(os.environ.get("CLASSIFICATION_AUTO_ACCEPT_THRESHOLD", "0.85"))
        if not 0 <= value <= 1:
            raise ValueError("CLASSIFICATION_AUTO_ACCEPT_THRESHOLD must be between 0 and 1")
        return cls(auto_accept_threshold=value)


@dataclass(frozen=True, slots=True)
class ClarificationView:
    """Owner-scoped clarification data ready for an API or UI adapter."""

    request: ClarificationRequest
    classification: AIClassification
    source_chunk: ContentChunk
    options: tuple[KnowledgeObject, ...]


class ClarificationError(Exception):
    """Base class for expected clarification workflow failures."""


class ClarificationNotFoundError(ClarificationError):
    """The requested clarification is not available to the owner."""


class InvalidClarificationError(ClarificationError):
    """The requested resolution is invalid or no longer applicable."""


class ClarificationService:
    """Keep uncertain AI classifications auditable and user-resolvable."""

    def __init__(self, session: Session, settings: ClarificationSettings | None = None) -> None:
        self.session = session
        self.settings = settings or ClarificationSettings.from_environment()

    def review_classifications(
        self, owner_id: int, artifact_ids: list[int]
    ) -> tuple[ClarificationRequest, ...]:
        """Auto-accept confident matches and create open requests for uncertainty."""

        requests: list[ClarificationRequest] = []
        classifications = self.session.scalars(
            select(AIClassification).where(
                AIClassification.owner_id == owner_id,
                AIClassification.artifact_id.in_(artifact_ids),
                AIClassification.deleted_at.is_(None),
            )
        )
        for classification in classifications:
            if classification.status != "suggested":
                continue
            if (
                classification.knowledge_object_id is not None
                and classification.confidence >= self.settings.auto_accept_threshold
            ):
                classification.status = "accepted"
                continue
            request = self.session.scalar(
                select(ClarificationRequest).where(
                    ClarificationRequest.owner_id == owner_id,
                    ClarificationRequest.classification_id == classification.id,
                    ClarificationRequest.status == "open",
                    ClarificationRequest.deleted_at.is_(None),
                )
            )
            if request is None:
                request = ClarificationRequest(
                    owner_id=owner_id,
                    classification_id=classification.id,
                    question=(f"Should this source be assigned to '{classification.label}'?"),
                    status="open",
                )
                self.session.add(request)
            requests.append(request)
        return tuple(requests)

    def list_open(self, owner_id: int) -> tuple[ClarificationView, ...]:
        """Return pending requests with evidence and owner-scoped choices."""

        requests = self.session.scalars(
            select(ClarificationRequest)
            .where(
                ClarificationRequest.owner_id == owner_id,
                ClarificationRequest.status == "open",
                ClarificationRequest.deleted_at.is_(None),
            )
            .order_by(ClarificationRequest.created_at)
        )
        return tuple(self._view(request, owner_id) for request in requests)

    def resolve(
        self,
        owner_id: int,
        clarification_id: int,
        *,
        action: ClarificationAction,
        selected_knowledge_object_ids: list[int],
        new_topic_title: str | None = None,
    ) -> ClarificationView:
        """Record an auditable user decision without erasing the AI proposal."""

        request = self.session.scalar(
            select(ClarificationRequest).where(
                ClarificationRequest.id == clarification_id,
                ClarificationRequest.owner_id == owner_id,
                ClarificationRequest.deleted_at.is_(None),
            )
        )
        if request is None:
            raise ClarificationNotFoundError("Clarification request does not exist")
        if request.status != "open":
            raise InvalidClarificationError("Clarification request is already resolved")
        classification = self._classification(request)
        selected_ids = list(dict.fromkeys(selected_knowledge_object_ids))
        if action == "reject":
            if selected_ids or new_topic_title:
                raise InvalidClarificationError("Reject cannot include an assignment")
        elif action == "accept" and not selected_ids:
            if classification.knowledge_object_id is None:
                raise InvalidClarificationError("Accept requires a knowledge object")
            selected_ids = [classification.knowledge_object_id]
        elif action in {"edit", "assign"} and not selected_ids and not new_topic_title:
            raise InvalidClarificationError("An edit or assignment requires a target")

        if new_topic_title:
            title = new_topic_title.strip()
            if not title:
                raise InvalidClarificationError("New topic title must not be blank")
            topic = KnowledgeObject(owner_id=owner_id, kind="topic", title=title)
            self.session.add(topic)
            self.session.flush()
            selected_ids.append(topic.id)
        selected_ids = list(dict.fromkeys(selected_ids))
        options = tuple(
            self.session.scalars(
                select(KnowledgeObject).where(
                    KnowledgeObject.owner_id == owner_id,
                    KnowledgeObject.id.in_(selected_ids),
                    KnowledgeObject.deleted_at.is_(None),
                )
            )
        )
        if len(options) != len(selected_ids):
            raise InvalidClarificationError("One or more selected objects are unavailable")

        if selected_ids:
            classification.knowledge_object_id = selected_ids[0]
            classification.status = "accepted"
            for object_id in selected_ids[1:]:
                self.session.add(
                    AIClassification(
                        owner_id=owner_id,
                        content_chunk_id=classification.content_chunk_id,
                        knowledge_object_id=object_id,
                        artifact_id=classification.artifact_id,
                        label=classification.label,
                        confidence=classification.confidence,
                        status="accepted",
                    )
                )
        else:
            classification.status = "rejected"
        request.status = "resolved"
        request.resolution = json.dumps(
            {
                "action": action,
                "selected_knowledge_object_ids": selected_ids,
                "new_topic_title": new_topic_title,
            },
            sort_keys=True,
        )
        request.selected_knowledge_object_ids = selected_ids
        request.selected_knowledge_object_id = selected_ids[0] if selected_ids else None
        request.resolved_at = datetime.now(UTC)
        self._finalize_source_if_clear(owner_id, classification)
        self.session.commit()
        return self._view(request, owner_id)

    def _finalize_source_if_clear(self, owner_id: int, classification: AIClassification) -> None:
        """Return a source to ready when its active clarification queue is empty."""

        artifact = self.session.scalar(
            select(DerivedArtifact).where(DerivedArtifact.id == classification.artifact_id)
        )
        source_id = artifact.metadata_json.get("source_file_id") if artifact else None
        if not isinstance(source_id, int):
            return
        pending = self.session.scalar(
            select(ClarificationRequest.id)
            .join(AIClassification, ClarificationRequest.classification_id == AIClassification.id)
            .join(DerivedArtifact, AIClassification.artifact_id == DerivedArtifact.id)
            .where(
                ClarificationRequest.owner_id == owner_id,
                ClarificationRequest.status == "open",
                ClarificationRequest.deleted_at.is_(None),
                DerivedArtifact.metadata_json["source_file_id"].as_integer() == source_id,
                DerivedArtifact.metadata_json["active"].as_boolean().is_(True),
            )
            .limit(1)
        )
        if pending is not None:
            return
        source = self.session.scalar(
            select(SourceFile).where(
                SourceFile.id == source_id,
                SourceFile.owner_id == owner_id,
                SourceFile.deleted_at.is_(None),
            )
        )
        if source is None or source.ingestion_status != "needs_input":
            return
        timeline = list(source.metadata_json.get("status_timeline", []))
        timeline.append({"status": "ready", "at": datetime.now(UTC).isoformat()})
        source.metadata_json = {
            **source.metadata_json,
            "status_timeline": timeline,
            "progress": 1.0,
        }
        source.ingestion_status = "ready"
        job = self.session.scalar(
            select(ProcessingJob)
            .where(
                ProcessingJob.subject_type == "source_file",
                ProcessingJob.subject_id == source_id,
            )
            .order_by(ProcessingJob.id.desc())
        )
        if job is not None:
            job.status = "succeeded"
            job.metadata_json = {**job.metadata_json, "stage": "ready", "progress": 1.0}

    def _view(self, request: ClarificationRequest, owner_id: int) -> ClarificationView:
        classification = self._classification(request)
        chunk = self.session.scalar(
            select(ContentChunk).where(ContentChunk.id == classification.content_chunk_id)
        )
        if chunk is None:
            raise ClarificationNotFoundError("Clarification source evidence is unavailable")
        options = tuple(
            self.session.scalars(
                select(KnowledgeObject)
                .where(
                    KnowledgeObject.owner_id == owner_id,
                    KnowledgeObject.deleted_at.is_(None),
                )
                .order_by(KnowledgeObject.title)
            )
        )
        return ClarificationView(request, classification, chunk, options)

    def _classification(self, request: ClarificationRequest) -> AIClassification:
        if request.classification_id is None:
            raise ClarificationNotFoundError("Clarification has no classification proposal")
        classification = self.session.scalar(
            select(AIClassification).where(AIClassification.id == request.classification_id)
        )
        if classification is None:
            raise ClarificationNotFoundError("Classification proposal does not exist")
        return classification
