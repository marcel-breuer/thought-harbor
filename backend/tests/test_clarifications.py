from datetime import datetime
from typing import Any

import pytest

from thoughtharbor.domain.models import (
    AIClassification,
    ClarificationRequest,
    ContentChunk,
    KnowledgeObject,
)
from thoughtharbor.knowledge.clarifications import (
    ClarificationService,
    ClarificationSettings,
    InvalidClarificationError,
)


def test_low_confidence_classification_creates_a_request() -> None:
    classification = AIClassification(
        id=1,
        owner_id=7,
        content_chunk_id=12,
        artifact_id=20,
        label="Project Aurora",
        confidence=0.4,
        status="suggested",
    )
    session = FakeSession(scalars_results=[[classification]], scalar_results=[None])

    requests = ClarificationService(
        session,
        ClarificationSettings(auto_accept_threshold=0.85),  # type: ignore[arg-type]
    ).review_classifications(7, [20])

    assert len(requests) == 1
    assert requests[0].question == "Should this source be assigned to 'Project Aurora'?"
    assert requests[0].status == "open"
    assert session.added[0] is requests[0]


def test_confident_existing_match_is_auto_accepted() -> None:
    classification = AIClassification(
        id=1,
        owner_id=7,
        content_chunk_id=12,
        artifact_id=20,
        knowledge_object_id=30,
        label="Project Aurora",
        confidence=0.95,
        status="suggested",
    )
    session = FakeSession(scalars_results=[[classification]])

    requests = ClarificationService(session).review_classifications(7, [20])

    assert requests == ()
    assert classification.status == "accepted"


def test_resolution_preserves_audit_data_and_supports_multiple_assignments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = ClarificationRequest(
        id=5,
        owner_id=7,
        classification_id=1,
        question="Assign this source?",
        status="open",
        created_at=datetime.now(),
    )
    classification = AIClassification(
        id=1,
        owner_id=7,
        content_chunk_id=12,
        artifact_id=20,
        label="Projects",
        confidence=0.3,
        status="suggested",
    )
    options = [
        KnowledgeObject(id=30, owner_id=7, kind="project", title="Aurora"),
        KnowledgeObject(id=31, owner_id=7, kind="topic", title="Operations"),
    ]
    session = FakeSession(
        scalar_results=[
            request,
            classification,
            classification,
            ContentChunk(id=12, owner_id=7, document_id=3, sequence=0, text="Evidence"),
        ],
        scalars_results=[options, options],
    )
    service = ClarificationService(session)  # type: ignore[arg-type]
    monkeypatch.setattr(service, "_finalize_source_if_clear", lambda owner_id, value: None)

    result = service.resolve(
        7,
        5,
        action="assign",
        selected_knowledge_object_ids=[30, 31],
    )

    assert result.request.status == "resolved"
    assert result.request.selected_knowledge_object_ids == [30, 31]
    assert '"action": "assign"' in (result.request.resolution or "")
    assert classification.status == "accepted"
    assert classification.knowledge_object_id == 30
    assert any(
        isinstance(value, AIClassification) and value.knowledge_object_id == 31
        for value in session.added
    )


def test_accept_without_a_target_is_rejected() -> None:
    request = ClarificationRequest(
        id=5,
        owner_id=7,
        classification_id=1,
        question="Assign this source?",
        status="open",
    )
    classification = AIClassification(
        id=1,
        owner_id=7,
        content_chunk_id=12,
        artifact_id=20,
        label="Projects",
        confidence=0.3,
        status="suggested",
    )
    session = FakeSession(scalar_results=[request, classification])

    with pytest.raises(InvalidClarificationError):
        ClarificationService(session).resolve(
            7, 5, action="accept", selected_knowledge_object_ids=[]
        )


class FakeSession:
    def __init__(
        self,
        *,
        scalars_results: list[list[Any]] | None = None,
        scalar_results: list[Any] | None = None,
    ) -> None:
        self.scalars_results = scalars_results or []
        self.scalar_results = scalar_results or []
        self.added: list[Any] = []
        self._next_id = 100

    def scalar(self, statement: Any) -> Any:
        return self.scalar_results.pop(0) if self.scalar_results else None

    def scalars(self, statement: Any) -> list[Any]:
        return self.scalars_results.pop(0) if self.scalars_results else []

    def add(self, value: Any) -> None:
        self.added.append(value)

    def flush(self) -> None:
        for value in self.added:
            if isinstance(value, KnowledgeObject) and value.id is None:
                value.id = self._next_id
                self._next_id += 1

    def commit(self) -> None:
        pass
