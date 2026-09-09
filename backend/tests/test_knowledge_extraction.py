import asyncio
from typing import Any

import pytest
from pydantic import BaseModel

from thoughtharbor.ai.models import ExtractionResult, ModelMetadata
from thoughtharbor.domain.models import ContentChunk, DerivedArtifact, SourceFile
from thoughtharbor.knowledge.extraction import (
    ArtifactDraft,
    KnowledgeExtraction,
    KnowledgeExtractionError,
    KnowledgeExtractionService,
)


def model_metadata() -> ModelMetadata:
    return ModelMetadata(
        provider="test",
        model="test-model",
        model_version="1",
        capabilities=("structured_extraction",),
        context_window=None,
        max_output_tokens=None,
        configuration_fingerprint="test-fingerprint",
    )


def test_extraction_prompt_includes_chunk_ids_and_locations() -> None:
    captured: dict[str, Any] = {}

    class FakeRuntime:
        async def extract(self, request, schema: type[BaseModel]):
            captured["request"] = request
            captured["schema"] = schema
            return ExtractionResult(
                value=KnowledgeExtraction(
                    artifacts=[
                        ArtifactDraft(
                            kind="summary",
                            content="A useful summary",
                            source_chunk_ids=[12],
                        )
                    ]
                ),
                metadata=model_metadata(),
            )

    chunk = ContentChunk(
        id=12,
        owner_id=7,
        document_id=3,
        sequence=0,
        text="Source evidence",
        source_offset_start=10,
        source_offset_end=25,
        location={"page": 2},
    )
    service = KnowledgeExtractionService(None, FakeRuntime())  # type: ignore[arg-type]

    result = asyncio.run(service._extract((chunk,)))

    assert result.value.artifacts[0].source_chunk_ids == [12]
    assert "source_chunk_id=12" in captured["request"].messages[1].content
    assert '"page": 2' in captured["request"].messages[1].content
    assert captured["schema"] is KnowledgeExtraction


def test_persisted_artifacts_are_replaced_as_a_new_version() -> None:
    session = FakeSession()
    source = SourceFile(
        id=7,
        owner_id=42,
        storage_key="uploads/source",
        original_name="notes.txt",
        byte_size=10,
        sha256="a" * 64,
        metadata_json={},
    )
    chunk = ContentChunk(id=12, owner_id=42, document_id=3, sequence=0, text="Evidence")
    service = KnowledgeExtractionService(session)  # type: ignore[arg-type]
    extraction = KnowledgeExtraction(
        artifacts=[
            ArtifactDraft(
                kind="decision",
                title="Decision",
                content="Use the local runtime",
                source_chunk_ids=[12],
                confidence=0.9,
            )
        ]
    )

    first = service._persist(source, (chunk,), extraction, model_metadata())
    session.scalar_results.append(list(first))
    second = service._persist(source, (chunk,), extraction, model_metadata())

    assert first[0].metadata_json["version"] == 1
    assert second[0].metadata_json["version"] == 2
    assert first[0].metadata_json["active"] is False
    assert first[0].metadata_json["superseded_by"] == [second[0].id]
    assert second[0].metadata_json["replaces"] == [first[0].id]
    assert any(isinstance(value, DerivedArtifact) for value in session.added)


def test_artifact_evidence_must_belong_to_the_source() -> None:
    service = KnowledgeExtractionService(None)  # type: ignore[arg-type]
    source = SourceFile(
        id=7,
        owner_id=42,
        storage_key="uploads/source",
        original_name="notes.txt",
        byte_size=10,
        sha256="a" * 64,
        metadata_json={},
    )
    chunk = ContentChunk(id=12, owner_id=42, document_id=3, sequence=0, text="Evidence")
    extraction = KnowledgeExtraction(
        artifacts=[ArtifactDraft(kind="summary", content="Summary", source_chunk_ids=[999])]
    )

    with pytest.raises(KnowledgeExtractionError):
        service._persist(source, (chunk,), extraction, model_metadata())


class FakeSession:
    def __init__(self) -> None:
        self.added: list[Any] = []
        self.scalar_results: list[list[Any]] = [[]]
        self._next_id = 100

    def add(self, value: Any) -> None:
        self.added.append(value)

    def flush(self) -> None:
        for value in self.added:
            if isinstance(value, DerivedArtifact) and value.id is None:
                value.id = self._next_id
                self._next_id += 1

    def scalars(self, statement: Any) -> list[Any]:
        return self.scalar_results.pop(0) if self.scalar_results else []
