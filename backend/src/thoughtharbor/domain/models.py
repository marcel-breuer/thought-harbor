"""SQLAlchemy persistence models for the ThoughtHarbor knowledge graph."""

from datetime import datetime
from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all persistence models."""


class TimestampMixin:
    """Consistent timezone-aware lifecycle timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    username: Mapped[str | None] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False, default="admin")
    display_name: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("role IN ('admin', 'user')", name="ck_user_role"),
        UniqueConstraint("username", name="uq_users_username"),
    )


class UserSession(TimestampMixin, Base):
    __tablename__ = "user_sessions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (Index("ix_user_sessions_user_id", "user_id"),)


class SourceFile(TimestampMixin, Base):
    __tablename__ = "source_files"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    storage_key: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    original_name: Mapped[str] = mapped_column(Text, nullable=False)
    media_type: Mapped[str | None] = mapped_column(Text)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    ingestion_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        Index("ix_source_files_owner_id", "owner_id"),
        Index(
            "ix_source_files_owner_active",
            "owner_id",
            postgresql_where="deleted_at IS NULL",
        ),
    )


class Document(TimestampMixin, Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_file_id: Mapped[int] = mapped_column(
        ForeignKey("source_files.id", ondelete="RESTRICT"), nullable=False
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    extracted_text: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        Index("ix_documents_owner_id", "owner_id"),
        Index("ix_documents_source_file_id", "source_file_id"),
    )


class Meeting(TimestampMixin, Base):
    __tablename__ = "meetings"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_file_id: Mapped[int | None] = mapped_column(
        ForeignKey("source_files.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        Index("ix_meetings_owner_id", "owner_id"),
        Index("ix_meetings_source_file_id", "source_file_id"),
    )


class Speaker(TimestampMixin, Base):
    __tablename__ = "speakers"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    meeting_id: Mapped[int | None] = mapped_column(ForeignKey("meetings.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_speakers_owner_id", "owner_id"),
        Index("ix_speakers_meeting_id", "meeting_id"),
        UniqueConstraint("meeting_id", "label", name="uq_speakers_meeting_label"),
    )


class Transcript(TimestampMixin, Base):
    __tablename__ = "transcripts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    meeting_id: Mapped[int] = mapped_column(
        ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    language: Mapped[str | None] = mapped_column(String(16))
    provider: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_transcripts_owner_id", "owner_id"),
        Index("ix_transcripts_meeting_id", "meeting_id"),
    )


class TranscriptSegment(TimestampMixin, Base):
    __tablename__ = "transcript_segments"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    transcript_id: Mapped[int] = mapped_column(
        ForeignKey("transcripts.id", ondelete="CASCADE"), nullable=False
    )
    speaker_id: Mapped[int | None] = mapped_column(ForeignKey("speakers.id", ondelete="SET NULL"))
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    start_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    end_ms: Mapped[int] = mapped_column(BigInteger, nullable=False)
    source_offset_start: Mapped[int | None] = mapped_column(Integer)
    source_offset_end: Mapped[int | None] = mapped_column(Integer)

    __table_args__ = (
        UniqueConstraint("transcript_id", "sequence", name="uq_transcript_segment_sequence"),
        CheckConstraint("start_ms >= 0 AND end_ms >= start_ms", name="ck_segment_time_range"),
        Index("ix_transcript_segments_transcript_id", "transcript_id"),
        Index("ix_transcript_segments_speaker_id", "speaker_id"),
    )


class ProcessingJob(TimestampMixin, Base):
    __tablename__ = "processing_jobs"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    job_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    subject_type: Mapped[str | None] = mapped_column(String(64))
    subject_id: Mapped[int | None] = mapped_column(BigInteger)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        Index("ix_processing_jobs_owner_id", "owner_id"),
        Index("ix_processing_jobs_status_created_at", "status", "created_at"),
    )


class ProcessingAttempt(TimestampMixin, Base):
    __tablename__ = "processing_attempts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    job_id: Mapped[int] = mapped_column(
        ForeignKey("processing_jobs.id", ondelete="CASCADE"), nullable=False
    )
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(64))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        UniqueConstraint("job_id", "attempt_number", name="uq_processing_attempt_number"),
        Index("ix_processing_attempts_job_id", "job_id"),
    )


class KnowledgeObject(TimestampMixin, Base):
    __tablename__ = "knowledge_objects"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ('topic', 'project', 'person', 'organization', 'custom')",
            name="ck_knowledge_object_kind",
        ),
        Index("ix_knowledge_objects_owner_id", "owner_id"),
        Index("ix_knowledge_objects_owner_kind", "owner_id", "kind"),
    )


class KnowledgeRelation(TimestampMixin, Base):
    __tablename__ = "knowledge_relations"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    source_object_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_objects.id", ondelete="CASCADE"), nullable=False
    )
    target_object_id: Mapped[int] = mapped_column(
        ForeignKey("knowledge_objects.id", ondelete="CASCADE"), nullable=False
    )
    relation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float | None] = mapped_column()
    source_artifact_id: Mapped[int | None] = mapped_column(
        ForeignKey("derived_artifacts.id", ondelete="SET NULL")
    )

    __table_args__ = (
        CheckConstraint(
            "source_object_id <> target_object_id", name="ck_relation_distinct_objects"
        ),
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_relation_confidence",
        ),
        UniqueConstraint(
            "source_object_id", "target_object_id", "relation_type", name="uq_knowledge_relation"
        ),
        Index("ix_knowledge_relations_owner_id", "owner_id"),
        Index("ix_knowledge_relations_source_object_id", "source_object_id"),
        Index("ix_knowledge_relations_target_object_id", "target_object_id"),
    )


class ContentChunk(TimestampMixin, Base):
    __tablename__ = "content_chunks"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[int | None] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    transcript_segment_id: Mapped[int | None] = mapped_column(
        ForeignKey("transcript_segments.id", ondelete="CASCADE")
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    source_offset_start: Mapped[int | None] = mapped_column(Integer)
    source_offset_end: Mapped[int | None] = mapped_column(Integer)
    source_start_ms: Mapped[int | None] = mapped_column(BigInteger)
    source_end_ms: Mapped[int | None] = mapped_column(BigInteger)
    location: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    __table_args__ = (
        CheckConstraint(
            "(document_id IS NOT NULL) <> (transcript_segment_id IS NOT NULL)",
            name="ck_chunk_single_source",
        ),
        Index("ix_content_chunks_owner_id", "owner_id"),
        Index("ix_content_chunks_document_sequence", "document_id", "sequence"),
        Index("ix_content_chunks_transcript_sequence", "transcript_segment_id", "sequence"),
    )


class Embedding(TimestampMixin, Base):
    __tablename__ = "embeddings"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content_chunk_id: Mapped[int] = mapped_column(
        ForeignKey("content_chunks.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str | None] = mapped_column(Text)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False, default=768)
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)

    __table_args__ = (
        CheckConstraint("dimension = 768", name="ck_embedding_dimension"),
        UniqueConstraint(
            "content_chunk_id",
            "provider",
            "model",
            "model_version",
            name="uq_embedding_model_per_chunk",
        ),
        Index("ix_embeddings_owner_id", "owner_id"),
        Index(
            "ix_embeddings_vector_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class DerivedArtifact(TimestampMixin, Base):
    __tablename__ = "derived_artifacts"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str | None] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_origin: Mapped[str] = mapped_column(String(16), nullable=False, default="derived")
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        CheckConstraint(
            "kind IN ("
            "'summary', 'statement', 'classification', 'suggestion', 'decision', "
            "'task', 'open_question', 'idea')",
            name="ck_derived_artifact_kind",
        ),
        CheckConstraint("content_origin = 'derived'", name="ck_derived_artifact_origin"),
        Index("ix_derived_artifacts_owner_kind", "owner_id", "kind"),
    )


class ArtifactSource(TimestampMixin, Base):
    __tablename__ = "artifact_sources"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    artifact_id: Mapped[int] = mapped_column(
        ForeignKey("derived_artifacts.id", ondelete="CASCADE"), nullable=False
    )
    content_chunk_id: Mapped[int] = mapped_column(
        ForeignKey("content_chunks.id", ondelete="RESTRICT"), nullable=False
    )
    source_role: Mapped[str | None] = mapped_column(String(32))
    supporting_excerpt: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        UniqueConstraint("artifact_id", "content_chunk_id", name="uq_artifact_source_chunk"),
        Index("ix_artifact_sources_artifact_id", "artifact_id"),
        Index("ix_artifact_sources_content_chunk_id", "content_chunk_id"),
    )


class ArtifactGeneration(TimestampMixin, Base):
    __tablename__ = "artifact_generations"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    artifact_id: Mapped[int] = mapped_column(
        ForeignKey("derived_artifacts.id", ondelete="CASCADE"), nullable=False
    )
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str | None] = mapped_column(Text)
    prompt_name: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[float | None] = mapped_column()
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSONB, nullable=False, default=dict
    )

    __table_args__ = (
        CheckConstraint(
            "confidence IS NULL OR (confidence >= 0 AND confidence <= 1)",
            name="ck_artifact_generation_confidence",
        ),
        Index("ix_artifact_generations_artifact_id", "artifact_id"),
    )


class Decision(TimestampMixin, Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    artifact_id: Mapped[int] = mapped_column(
        ForeignKey("derived_artifacts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")


class Task(TimestampMixin, Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    artifact_id: Mapped[int] = mapped_column(
        ForeignKey("derived_artifacts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    assignee_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (Index("ix_tasks_assignee_user_id", "assignee_user_id"),)


class OpenQuestion(TimestampMixin, Base):
    __tablename__ = "open_questions"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    artifact_id: Mapped[int] = mapped_column(
        ForeignKey("derived_artifacts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")


class Idea(TimestampMixin, Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    artifact_id: Mapped[int] = mapped_column(
        ForeignKey("derived_artifacts.id", ondelete="CASCADE"), nullable=False, unique=True
    )


class AIClassification(TimestampMixin, Base):
    __tablename__ = "ai_classifications"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    content_chunk_id: Mapped[int] = mapped_column(
        ForeignKey("content_chunks.id", ondelete="CASCADE"), nullable=False
    )
    knowledge_object_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_objects.id", ondelete="SET NULL")
    )
    artifact_id: Mapped[int | None] = mapped_column(
        ForeignKey("derived_artifacts.id", ondelete="SET NULL")
    )
    label: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="suggested")

    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_classification_confidence"),
        Index("ix_ai_classifications_owner_id", "owner_id"),
        Index("ix_ai_classifications_content_chunk_id", "content_chunk_id"),
    )


class ClarificationRequest(TimestampMixin, Base):
    __tablename__ = "clarification_requests"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    classification_id: Mapped[int | None] = mapped_column(
        ForeignKey("ai_classifications.id", ondelete="SET NULL")
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
    resolution: Mapped[str | None] = mapped_column(Text)
    selected_knowledge_object_ids: Mapped[list[int]] = mapped_column(
        JSONB, nullable=False, default=list
    )
    selected_knowledge_object_id: Mapped[int | None] = mapped_column(
        ForeignKey("knowledge_objects.id", ondelete="SET NULL")
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("ix_clarification_requests_owner_status", "owner_id", "status"),
        Index("ix_clarification_requests_classification_id", "classification_id"),
    )
