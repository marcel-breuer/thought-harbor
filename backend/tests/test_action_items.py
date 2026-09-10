from datetime import UTC, datetime
from typing import Any

import pytest

from thoughtharbor.domain.models import ContentChunk, DerivedArtifact, Document, SourceFile, Task
from thoughtharbor.knowledge.action_items import (
    ActionItemService,
    InvalidActionItemStatusError,
)

NOW = datetime(2026, 9, 10, tzinfo=UTC)


def artifact(artifact_id: int, kind: str, title: str) -> DerivedArtifact:
    return DerivedArtifact(
        id=artifact_id,
        owner_id=7,
        kind=kind,
        title=title,
        content=f"{title} details",
        metadata_json={"active": True},
        created_at=NOW,
        updated_at=NOW,
    )


def test_list_returns_all_action_types_and_filters_status() -> None:
    items = [
        artifact(1, "task", "Send proposal"),
        artifact(2, "decision", "Use local processing"),
        artifact(3, "open_question", "Who owns migration?"),
    ]
    session = FakeSession(
        scalar_results=[
            Task(id=11, artifact_id=1, status="in_progress"),
            type("DecisionRecord", (), {"status": "active"})(),
            type("QuestionRecord", (), {"status": "open"})(),
        ],
        scalars_results=[items, [], [], [], [], [], []],
    )

    result, total = ActionItemService(session).list(
        7,
        item_type=None,
        status="in_progress",
        topic_id=None,
        project_id=None,
        source_type=None,
        assignee_user_id=None,
        date_from=None,
        date_to=None,
        page=1,
        page_size=25,
    )

    assert total == 1
    assert [item.artifact.title for item in result] == ["Send proposal"]
    assert result[0].item_type == "task"


def test_status_update_preserves_source_and_appends_history() -> None:
    item = artifact(1, "task", "Send proposal")
    task = Task(id=11, artifact_id=1, status="open")
    session = FakeSession(
        scalar_results=[item, task, task, item, task],
        scalars_results=[[], [], []],
    )

    result = ActionItemService(session).update_status(7, 1, "done")

    assert result.status == "done"
    assert result.artifact.content == "Send proposal details"
    assert task.status == "done"
    assert result.artifact.metadata_json["status_history"][0]["previous_status"] == "open"
    assert session.commits == 1


def test_invalid_status_is_rejected_for_the_action_type() -> None:
    item = artifact(1, "task", "Send proposal")
    session = FakeSession(scalar_results=[item, Task(id=11, artifact_id=1, status="open")])

    with pytest.raises(InvalidActionItemStatusError):
        ActionItemService(session).update_status(7, 1, "resolved")

    assert session.commits == 0


def test_source_context_is_returned_for_document_action_items() -> None:
    item = artifact(1, "task", "Send proposal")
    chunk = ContentChunk(
        id=21,
        owner_id=7,
        document_id=31,
        sequence=0,
        text="Please send the revised proposal.",
        source_offset_start=4,
        source_offset_end=39,
        location={"page": 2},
    )
    document = Document(
        id=31,
        owner_id=7,
        source_file_id=41,
        title="Q2 planning",
        extracted_text=chunk.text,
        metadata_json={},
    )
    source = SourceFile(
        id=41,
        owner_id=7,
        storage_key="uploads/q2",
        original_name="q2.txt",
        media_type="text/plain",
        byte_size=10,
        sha256="a" * 64,
        ingestion_status="ready",
        metadata_json={"source_type": "document"},
    )
    session = FakeSession(
        scalar_results=[item, Task(id=11, artifact_id=1), document, source],
        scalars_results=[[], [chunk]],
    )

    result = ActionItemService(session).get(7, 1)

    assert result.sources[0].title == "Q2 planning"
    assert result.sources[0].source_file_id == 41
    assert result.sources[0].chunk.source_offset_start == 4


class FakeSession:
    def __init__(
        self,
        *,
        scalar_results: list[Any] | None = None,
        scalars_results: list[list[Any]] | None = None,
    ) -> None:
        self.scalar_results = scalar_results or []
        self.scalars_results = scalars_results or []
        self.commits = 0

    def scalar(self, statement: Any) -> Any:
        return self.scalar_results.pop(0) if self.scalar_results else None

    def scalars(self, statement: Any) -> list[Any]:
        return self.scalars_results.pop(0) if self.scalars_results else []

    def commit(self) -> None:
        self.commits += 1
