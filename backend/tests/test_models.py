from sqlalchemy import CheckConstraint

from thoughtharbor.domain.models import (
    ArtifactSource,
    Base,
    ContentChunk,
    DerivedArtifact,
    Embedding,
    Speaker,
)

EXPECTED_TABLES = {
    "users",
    "user_sessions",
    "source_files",
    "documents",
    "meetings",
    "speakers",
    "transcripts",
    "transcript_segments",
    "processing_jobs",
    "processing_attempts",
    "knowledge_objects",
    "knowledge_relations",
    "content_chunks",
    "embeddings",
    "derived_artifacts",
    "artifact_sources",
    "artifact_generations",
    "decisions",
    "tasks",
    "open_questions",
    "ideas",
    "ai_classifications",
    "clarification_requests",
}


def test_all_knowledge_tables_are_registered() -> None:
    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_provenance_and_source_constraints_are_explicit() -> None:
    chunk_constraints = {
        constraint.name
        for constraint in ContentChunk.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    artifact_constraints = {
        constraint.name
        for constraint in DerivedArtifact.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }

    assert "ck_chunk_single_source" in chunk_constraints
    assert "ck_derived_artifact_origin" in artifact_constraints
    assert {
        foreign_key.target_fullname
        for foreign_key in ArtifactSource.__table__.c.artifact_id.foreign_keys
    } == {"derived_artifacts.id"}
    assert {
        foreign_key.target_fullname
        for foreign_key in ArtifactSource.__table__.c.content_chunk_id.foreign_keys
    } == {"content_chunks.id"}


def test_embedding_dimension_is_recorded_and_constrained() -> None:
    assert Embedding.__table__.c.embedding.type.dim == 768
    constraints = {
        constraint.name
        for constraint in Embedding.__table__.constraints
        if isinstance(constraint, CheckConstraint)
    }
    assert "ck_embedding_dimension" in constraints


def test_speakers_are_scoped_to_meetings() -> None:
    assert Speaker.__table__.c.meeting_id.foreign_keys
    assert "uq_speakers_meeting_label" in {
        constraint.name for constraint in Speaker.__table__.constraints
    }
