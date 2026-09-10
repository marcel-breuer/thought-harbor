from datetime import UTC, datetime
from typing import Any

from thoughtharbor.domain.models import (
    DerivedArtifact,
    Document,
    KnowledgeObject,
    Meeting,
    ProcessingJob,
    SourceFile,
    Task,
)
from thoughtharbor.knowledge.dashboard import DashboardService

NOW = datetime(2026, 9, 10, tzinfo=UTC)


def test_dashboard_aggregates_persisted_attention_without_generating_insights() -> None:
    source = SourceFile(
        id=1,
        owner_id=7,
        storage_key="uploads/one",
        original_name="planning.txt",
        media_type="text/plain",
        byte_size=10,
        sha256="a" * 64,
        ingestion_status="ready",
        metadata_json={"source_type": "transcript"},
        created_at=NOW,
        updated_at=NOW,
    )
    document = Document(
        id=2,
        owner_id=7,
        source_file_id=1,
        title="Planning",
        created_at=NOW,
        updated_at=NOW,
    )
    meeting = Meeting(id=3, owner_id=7, source_file_id=None, title="Standup")
    job = ProcessingJob(
        id=4,
        owner_id=7,
        job_type="transcript_ingestion",
        status="failed",
        subject_type="source_file",
        subject_id=1,
        created_at=NOW,
        updated_at=NOW,
    )
    artifact = DerivedArtifact(
        id=5,
        owner_id=7,
        kind="task",
        title="Send notes",
        content="Send the meeting notes.",
        metadata_json={"active": True},
        created_at=NOW,
        updated_at=NOW,
    )
    topic = KnowledgeObject(
        id=6,
        owner_id=7,
        kind="topic",
        title="Planning",
        created_at=NOW,
        updated_at=NOW,
    )
    session = FakeSession(
        scalars_results=[[source], [document], [meeting], [job], [artifact], [topic]],
        scalar_results=[Task(id=7, artifact_id=5, status="open")],
    )

    result = DashboardService(session).get(7)

    assert result.recent_sources[0].document_id == 2
    assert result.processing_attention[0].status == "failed"
    assert result.open_tasks[0].title == "Send notes"
    assert result.active_topics[0].title == "Planning"
    assert result.insights == ()


class FakeSession:
    def __init__(
        self,
        *,
        scalars_results: list[list[Any]],
        scalar_results: list[Any],
    ) -> None:
        self.scalars_results = scalars_results
        self.scalar_results = scalar_results

    def scalars(self, statement: Any) -> list[Any]:
        return self.scalars_results.pop(0)

    def scalar(self, statement: Any) -> Any:
        return self.scalar_results.pop(0) if self.scalar_results else None

    def execute(self, statement: Any) -> list[Any]:
        return []
