"""Shared indexing and hybrid search application services."""

import asyncio
import hashlib
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

from sqlalchemy import exists, func, or_, select
from sqlalchemy.orm import Session

from thoughtharbor.ai.errors import AIError
from thoughtharbor.ai.models import EmbeddingRequest, ModelMetadata
from thoughtharbor.ai.runtime import AIRuntime
from thoughtharbor.domain.models import (
    AIClassification,
    ContentChunk,
    Document,
    Embedding,
    KnowledgeObject,
    Meeting,
    ProcessingJob,
    SourceFile,
    Transcript,
    TranscriptSegment,
)
from thoughtharbor.search.chunking import chunk_text

MAX_CHUNK_CHARS = 1_200
CHUNK_OVERLAP_CHARS = 200
EMBEDDING_BATCH_SIZE = 32


class SearchIndexError(AIError):
    """Raised when indexing cannot preserve the configured vector contract."""


@dataclass(frozen=True, slots=True)
class SearchCandidate:
    """Provider-independent candidate used by the ranking function."""

    chunk_id: int
    text: str
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    recency_score: float = 0.0
    source_type_score: float = 0.0

    @property
    def score(self) -> float:
        """Return the stable weighted hybrid score."""

        return (
            self.semantic_score * 0.60
            + self.lexical_score * 0.25
            + self.recency_score * 0.10
            + self.source_type_score * 0.05
        )


def rank_candidates(candidates: tuple[SearchCandidate, ...]) -> tuple[SearchCandidate, ...]:
    """Rank candidates without a provider call, making ranking independently testable."""

    return tuple(sorted(candidates, key=lambda candidate: (-candidate.score, candidate.chunk_id)))


@dataclass(frozen=True, slots=True)
class SearchHit:
    """A ranked result with exact source context for API and MCP adapters."""

    candidate: SearchCandidate
    source_file_id: int
    source_type: str
    source_title: str | None
    document_id: int | None
    meeting_id: int | None
    location: dict[str, Any]
    source_offset_start: int | None
    source_offset_end: int | None
    source_start_ms: int | None
    source_end_ms: int | None


class SearchIndexService:
    """Create idempotent embeddings and queue controlled re-index operations."""

    def __init__(self, session: Session, runtime: AIRuntime | None = None) -> None:
        self.session = session
        self.runtime = runtime or AIRuntime.from_environment()

    def index_source(self, source_file_id: int) -> int:
        """Chunk and embed one source, reusing rows for the active model identity."""

        source = self.session.scalar(
            select(SourceFile).where(
                SourceFile.id == source_file_id,
                SourceFile.deleted_at.is_(None),
            )
        )
        if source is None:
            return 0
        chunks = self._ensure_search_chunks(source)
        if not chunks:
            return 0
        metadata = asyncio.run(self.runtime.embedding_provider.metadata())
        self._validate_metadata(metadata)
        count = self._upsert_embeddings(chunks, metadata)
        self.session.commit()
        return count

    def enqueue_source(self, source_file_id: int, *, force: bool = False) -> int | None:
        """Persist and enqueue an owner-scoped indexing job after ingestion."""

        source = self.session.scalar(
            select(SourceFile).where(
                SourceFile.id == source_file_id,
                SourceFile.deleted_at.is_(None),
            )
        )
        if source is None:
            return None
        latest = self.session.scalar(
            select(ProcessingJob)
            .where(
                ProcessingJob.owner_id == source.owner_id,
                ProcessingJob.job_type == "search_index",
                ProcessingJob.subject_type == "source_file",
                ProcessingJob.subject_id == source_file_id,
            )
            .order_by(ProcessingJob.id.desc())
        )
        if latest is not None and latest.status in {"queued", "running"}:
            return latest.id
        if latest is not None and latest.status == "succeeded" and not force:
            return latest.id

        job = ProcessingJob(
            owner_id=source.owner_id,
            job_type="search_index",
            status="queued",
            subject_type="source_file",
            subject_id=source_file_id,
            metadata_json={"stage": "queued", "source_file_id": source_file_id},
        )
        self.session.add(job)
        self.session.commit()
        try:
            from thoughtharbor.tasks.search import index_source_content

            index_source_content.delay(source_file_id)
        except Exception as error:
            job.status = "failed"
            job.metadata_json = {**job.metadata_json, "error": str(error)}
            self.session.commit()
            return job.id
        return job.id

    def _ensure_search_chunks(self, source: SourceFile) -> tuple[ContentChunk, ...]:
        base_chunks = self._source_chunks(source.id, source.owner_id)
        result: list[ContentChunk] = []
        for base in base_chunks:
            if base.location.get("search_excluded"):
                result.extend(
                    child
                    for child in base_chunks
                    if child.location.get("search_parent_chunk_id") == base.id
                )
                continue
            pieces = chunk_text(
                base.text,
                max_chars=MAX_CHUNK_CHARS,
                overlap_chars=CHUNK_OVERLAP_CHARS,
            )
            if len(pieces) <= 1:
                result.append(base)
                continue
            base.location = {**base.location, "search_excluded": True}
            for index, piece in enumerate(pieces):
                child = ContentChunk(
                    owner_id=base.owner_id,
                    document_id=base.document_id,
                    transcript_segment_id=base.transcript_segment_id,
                    sequence=base.sequence * 1_000_000 + index,
                    text=piece.text,
                    source_offset_start=_offset(base.source_offset_start, piece.start),
                    source_offset_end=_offset(base.source_offset_start, piece.end),
                    source_start_ms=base.source_start_ms,
                    source_end_ms=base.source_end_ms,
                    location={
                        **base.location,
                        "search_parent_chunk_id": base.id,
                        "search_chunk_index": index,
                        "search_relative_offset_start": piece.start,
                        "search_relative_offset_end": piece.end,
                    },
                )
                self.session.add(child)
                result.append(child)
        self.session.flush()
        return tuple(result)

    def _source_chunks(self, source_file_id: int, owner_id: int) -> tuple[ContentChunk, ...]:
        statement = (
            select(ContentChunk)
            .outerjoin(Document, ContentChunk.document_id == Document.id)
            .outerjoin(
                TranscriptSegment, ContentChunk.transcript_segment_id == TranscriptSegment.id
            )
            .outerjoin(Transcript, TranscriptSegment.transcript_id == Transcript.id)
            .outerjoin(Meeting, Transcript.meeting_id == Meeting.id)
            .where(
                ContentChunk.owner_id == owner_id,
                ContentChunk.deleted_at.is_(None),
                or_(
                    Document.source_file_id == source_file_id,
                    Meeting.source_file_id == source_file_id,
                ),
            )
            .order_by(ContentChunk.sequence)
        )
        return tuple(self.session.scalars(statement))

    def _upsert_embeddings(self, chunks: tuple[ContentChunk, ...], metadata: ModelMetadata) -> int:
        chunk_ids = tuple(chunk.id for chunk in chunks)
        existing = tuple(
            self.session.scalars(
                select(Embedding).where(
                    Embedding.content_chunk_id.in_(chunk_ids),
                    Embedding.provider == metadata.provider,
                    Embedding.model == metadata.model,
                    _model_version_filter(metadata.model_version),
                )
            )
        )
        existing_by_chunk = {item.content_chunk_id: item for item in existing}
        pending = tuple(
            chunk
            for chunk in chunks
            if (
                existing_by_chunk.get(chunk.id) is None
                or existing_by_chunk[chunk.id].content_hash != _content_hash(chunk.text)
            )
        )
        indexed = 0
        for offset in range(0, len(pending), EMBEDDING_BATCH_SIZE):
            batch = pending[offset : offset + EMBEDDING_BATCH_SIZE]
            result = asyncio.run(
                self.runtime.embed(EmbeddingRequest(tuple(item.text for item in batch)))
            )
            if len(result.vectors) != len(batch):
                raise SearchIndexError("Embedding provider returned an unexpected vector count")
            self._validate_metadata(result.metadata)
            for chunk, vector in zip(batch, result.vectors, strict=True):
                if len(vector) != 768:
                    raise SearchIndexError("Embedding vector dimension must be 768")
                embedding = existing_by_chunk.get(chunk.id)
                if embedding is None:
                    embedding = Embedding(
                        owner_id=chunk.owner_id,
                        content_chunk_id=chunk.id,
                        provider=result.metadata.provider,
                        model=result.metadata.model,
                        model_version=result.metadata.model_version,
                        dimension=len(vector),
                        embedding=list(vector),
                        content_hash=_content_hash(chunk.text),
                    )
                    self.session.add(embedding)
                else:
                    embedding.embedding = list(vector)
                    embedding.dimension = len(vector)
                    embedding.content_hash = _content_hash(chunk.text)
                indexed += 1
        return indexed

    @staticmethod
    def _validate_metadata(metadata: ModelMetadata) -> None:
        if "embeddings" not in metadata.capabilities:
            raise SearchIndexError("Configured AI model does not support embeddings")


@dataclass(frozen=True, slots=True)
class SearchFilters:
    """Owner-scoped search filters shared by API and future MCP callers."""

    source_type: str | None = None
    topic_id: int | None = None
    project_id: int | None = None
    meeting_id: int | None = None
    document_id: int | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


class SearchService:
    """Search indexed source chunks using PostgreSQL lexical and vector retrieval."""

    def __init__(self, session: Session, runtime: AIRuntime | None = None) -> None:
        self.session = session
        self.runtime = runtime or AIRuntime.from_environment()

    async def search(
        self,
        owner_id: int,
        query: str,
        *,
        filters: SearchFilters | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> tuple[tuple[SearchHit, ...], int]:
        """Return ranked, paginated hits; lexical retrieval remains available if AI is down."""

        filters = filters or SearchFilters()
        semantic_rows: tuple[Any, ...] = ()
        try:
            metadata = await self.runtime.embedding_provider.metadata()
            self._validate_metadata(metadata)
            embedding_result = await self.runtime.embed(EmbeddingRequest((query,)))
            vector = embedding_result.vectors[0]
            if len(vector) != 768:
                raise SearchIndexError("Embedding vector dimension must be 768")
            semantic_rows = tuple(
                self.session.execute(self._semantic_statement(owner_id, filters, vector, metadata))
            )
        except (AIError, IndexError):
            semantic_rows = ()
        lexical_rows = tuple(
            self.session.execute(self._lexical_statement(owner_id, filters, query))
        )
        hits = self._merge_rows(semantic_rows, lexical_rows)
        start = (page - 1) * page_size
        return tuple(hits[start : start + page_size]), len(hits)

    def _semantic_statement(
        self,
        owner_id: int,
        filters: SearchFilters,
        vector: tuple[float, ...],
        metadata: ModelMetadata,
    ) -> Any:
        distance = Embedding.embedding.cosine_distance(list(vector))
        return (
            self._base_statement(owner_id, filters)
            .add_columns((1 - distance).label("semantic_score"))
            .join(Embedding, Embedding.content_chunk_id == ContentChunk.id)
            .where(
                _embedding_owner_clause(owner_id),
                Embedding.provider == metadata.provider,
                Embedding.model == metadata.model,
                _model_version_filter(metadata.model_version),
            )
            .order_by(distance)
            .limit(500)
        )

    def _lexical_statement(self, owner_id: int, filters: SearchFilters, query: str) -> Any:
        lexical_score = func.ts_rank_cd(
            func.to_tsvector("simple", ContentChunk.text),
            func.plainto_tsquery("simple", query),
        )
        return (
            self._base_statement(owner_id, filters)
            .add_columns(lexical_score.label("lexical_score"))
            .where(
                or_(
                    lexical_score > 0,
                    ContentChunk.text.ilike(f"%{query}%"),
                )
            )
            .order_by(lexical_score.desc())
            .limit(500)
        )

    def _base_statement(self, owner_id: int, filters: SearchFilters) -> Any:
        statement = (
            select(ContentChunk, SourceFile, Document, Meeting)
            .select_from(ContentChunk)
            .outerjoin(Document, ContentChunk.document_id == Document.id)
            .outerjoin(
                TranscriptSegment, ContentChunk.transcript_segment_id == TranscriptSegment.id
            )
            .outerjoin(Transcript, TranscriptSegment.transcript_id == Transcript.id)
            .outerjoin(Meeting, Transcript.meeting_id == Meeting.id)
            .join(
                SourceFile,
                or_(
                    SourceFile.id == Document.source_file_id,
                    SourceFile.id == Meeting.source_file_id,
                ),
            )
            .where(
                ContentChunk.owner_id == owner_id,
                ContentChunk.deleted_at.is_(None),
                SourceFile.owner_id == owner_id,
                SourceFile.deleted_at.is_(None),
                Document.deleted_at.is_(None) | Document.id.is_(None),
                Meeting.deleted_at.is_(None) | Meeting.id.is_(None),
                ContentChunk.location["search_excluded"].as_boolean().is_not(True),
            )
        )
        if filters.source_type:
            statement = statement.where(
                SourceFile.metadata_json["source_type"].as_string() == filters.source_type
            )
        if filters.document_id is not None:
            statement = statement.where(ContentChunk.document_id == filters.document_id)
        if filters.meeting_id is not None:
            statement = statement.where(Meeting.id == filters.meeting_id)
        if filters.date_from is not None:
            statement = statement.where(SourceFile.created_at >= filters.date_from)
        if filters.date_to is not None:
            statement = statement.where(SourceFile.created_at <= filters.date_to)
        if filters.topic_id is not None:
            statement = statement.where(self._classification_exists(filters.topic_id, "topic"))
        if filters.project_id is not None:
            statement = statement.where(self._classification_exists(filters.project_id, "project"))
        return statement

    @staticmethod
    def _classification_exists(object_id: int, kind: str) -> Any:
        return exists(
            select(AIClassification.id)
            .join(KnowledgeObject, KnowledgeObject.id == AIClassification.knowledge_object_id)
            .where(
                AIClassification.content_chunk_id == ContentChunk.id,
                AIClassification.knowledge_object_id == object_id,
                KnowledgeObject.kind == kind,
                AIClassification.status == "accepted",
                AIClassification.deleted_at.is_(None),
            )
        )

    def _merge_rows(
        self, semantic_rows: tuple[Any, ...], lexical_rows: tuple[Any, ...]
    ) -> tuple[SearchHit, ...]:
        by_chunk: dict[int, SearchHit] = {}
        for rows, score_name in ((semantic_rows, "semantic"), (lexical_rows, "lexical")):
            for row in rows:
                self._merge_row(by_chunk, row, score_name)
        ordered = rank_candidates(tuple(hit.candidate for hit in by_chunk.values()))
        return tuple(replace(by_chunk[item.chunk_id], candidate=item) for item in ordered)

    @staticmethod
    def _merge_row(by_chunk: dict[int, SearchHit], row: Any, score_name: str) -> None:
        chunk, source, document, meeting, score = row
        current = by_chunk.get(chunk.id)
        semantic_score = current.candidate.semantic_score if current else 0.0
        lexical_score = current.candidate.lexical_score if current else 0.0
        if score_name == "semantic":
            semantic_score = max(semantic_score, float(score or 0))
        else:
            lexical_score = max(lexical_score, float(score or 0))
        candidate = SearchCandidate(
            chunk_id=chunk.id,
            text=chunk.text,
            semantic_score=min(1.0, max(0.0, semantic_score)),
            lexical_score=min(1.0, max(0.0, lexical_score)),
            recency_score=_recency_score(source.created_at),
            source_type_score=(
                1.0 if source.metadata_json.get("source_type") in {"document", "email"} else 0.8
            ),
        )
        by_chunk[chunk.id] = SearchHit(
            candidate=candidate,
            source_file_id=source.id,
            source_type=source.metadata_json.get("source_type", "document"),
            source_title=(
                document.title
                if document is not None
                else (meeting.title if meeting is not None else None)
            ),
            document_id=document.id if document is not None else None,
            meeting_id=meeting.id if meeting is not None else None,
            location=dict(chunk.location),
            source_offset_start=chunk.source_offset_start,
            source_offset_end=chunk.source_offset_end,
            source_start_ms=chunk.source_start_ms,
            source_end_ms=chunk.source_end_ms,
        )

    @staticmethod
    def _validate_metadata(metadata: ModelMetadata) -> None:
        SearchIndexService._validate_metadata(metadata)


def _offset(base: int | None, relative: int) -> int | None:
    return base + relative if base is not None else relative


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _model_version_filter(model_version: str | None) -> Any:
    return (
        Embedding.model_version.is_(None)
        if model_version is None
        else Embedding.model_version == model_version
    )


def _embedding_owner_clause(owner_id: int) -> Any:
    return Embedding.owner_id == owner_id


def _recency_score(created_at: datetime) -> float:
    age_days = max(0.0, (datetime.now(created_at.tzinfo) - created_at).total_seconds() / 86_400)
    return max(0.0, 1.0 - min(age_days, 365.0) / 365.0)
