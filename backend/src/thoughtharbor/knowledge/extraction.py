"""Provider-neutral structured knowledge extraction for normalized sources."""

import asyncio
import json
from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from thoughtharbor.ai.errors import AIError
from thoughtharbor.ai.models import ChatMessage, ExtractionRequest, ExtractionResult, ModelMetadata
from thoughtharbor.ai.runtime import AIRuntime
from thoughtharbor.domain.models import (
    AIClassification,
    ArtifactGeneration,
    ArtifactSource,
    ContentChunk,
    Decision,
    DerivedArtifact,
    Document,
    Idea,
    KnowledgeObject,
    Meeting,
    OpenQuestion,
    ProcessingAttempt,
    ProcessingJob,
    SourceFile,
    Task,
    Transcript,
    TranscriptSegment,
)

ArtifactKind = Literal[
    "summary",
    "statement",
    "classification",
    "suggestion",
    "decision",
    "task",
    "open_question",
    "idea",
]

PROMPT_NAME = "structured-knowledge-extraction"
PROMPT_VERSION = "1"
PIPELINE_VERSION = "1"


class ArtifactDraft(BaseModel):
    """One validated artifact proposal returned by the extraction provider."""

    kind: ArtifactKind
    title: str | None = Field(default=None, max_length=500)
    content: str = Field(min_length=1, max_length=20_000)
    source_chunk_ids: list[int] = Field(min_length=1, max_length=50)
    confidence: float | None = Field(default=None, ge=0, le=1)


class KnowledgeExtraction(BaseModel):
    """Complete schema-constrained output for one source processing run."""

    artifacts: list[ArtifactDraft] = Field(min_length=1, max_length=100)


class KnowledgeExtractionError(AIError):
    """Raised when validated output cannot be safely connected to source evidence."""


class KnowledgeExtractionService:
    """Extract and persist versioned, provenance-preserving knowledge artifacts."""

    def __init__(self, session: Session, runtime: AIRuntime | None = None) -> None:
        self.session = session
        self.runtime = runtime or AIRuntime.from_environment()

    def process(self, source_file_id: int) -> tuple[DerivedArtifact, ...] | None:
        """Run one extraction version for a parsed document or completed meeting."""

        source = self.session.scalar(
            select(SourceFile).where(
                SourceFile.id == source_file_id,
                SourceFile.deleted_at.is_(None),
            )
        )
        if source is None:
            return None
        chunks = self._source_chunks(source)
        job = self._processing_job(source_file_id)
        if job is None or not chunks:
            if job is not None:
                self._mark_failed(source, job, None, "No normalized source content is available")
            return None

        attempt = self._start_attempt(job)
        self._set_status(source, "extracting", 0.0)
        job.metadata_json = {**job.metadata_json, "stage": "extracting", "progress": 0.0}
        self.session.commit()
        try:
            extraction_result = asyncio.run(self._extract(chunks))
            extraction = KnowledgeExtraction.model_validate(extraction_result.value)
            artifacts = self._persist(source, chunks, extraction, extraction_result.metadata)
        except (AIError, ValueError) as error:
            self._mark_failed(source, job, attempt, str(error))
            return None

        attempt.status = "succeeded"
        attempt.finished_at = datetime.now(UTC)
        job.status = "succeeded"
        job.metadata_json = {
            **job.metadata_json,
            "stage": "ready",
            "progress": 1.0,
            "artifact_count": len(artifacts),
        }
        self._set_status(source, "ready", 1.0)
        self.session.commit()
        return artifacts

    async def _extract(self, chunks: tuple[ContentChunk, ...]) -> ExtractionResult[BaseModel]:
        source_text = "\n\n".join(
            f"[source_chunk_id={chunk.id} "
            f"location={json.dumps(chunk.location, sort_keys=True)}]\n{chunk.text}"
            for chunk in chunks
        )
        request = ExtractionRequest(
            messages=(
                ChatMessage("system", _SYSTEM_PROMPT),
                ChatMessage("user", source_text),
            ),
            schema_name="thought_harbor_knowledge_extraction",
            temperature=0.0,
        )
        return await self.runtime.extract(request, KnowledgeExtraction)

    def _persist(
        self,
        source: SourceFile,
        chunks: tuple[ContentChunk, ...],
        extraction: KnowledgeExtraction,
        model_metadata: ModelMetadata,
    ) -> tuple[DerivedArtifact, ...]:
        chunk_by_id = {chunk.id: chunk for chunk in chunks}
        normalized: list[tuple[ArtifactDraft, tuple[ContentChunk, ...]]] = []
        for draft in extraction.artifacts:
            if draft.kind == "classification" and not draft.title:
                raise KnowledgeExtractionError("Classification artifacts require a title")
            evidence = tuple(
                chunk_by_id[chunk_id]
                for chunk_id in dict.fromkeys(draft.source_chunk_ids)
                if chunk_id in chunk_by_id
            )
            if len(evidence) != len(dict.fromkeys(draft.source_chunk_ids)):
                raise KnowledgeExtractionError(
                    "Every extracted artifact must reference an input source chunk"
                )
            normalized.append((draft, evidence))

        old_artifacts = list(
            self.session.scalars(
                select(DerivedArtifact).where(
                    DerivedArtifact.owner_id == source.owner_id,
                    DerivedArtifact.deleted_at.is_(None),
                    DerivedArtifact.metadata_json["source_file_id"].as_integer() == source.id,
                )
            )
        )
        version = (
            max(
                (int(artifact.metadata_json.get("version", 0)) for artifact in old_artifacts),
                default=0,
            )
            + 1
        )
        run_id = str(uuid4())
        metadata_base = {
            "source_file_id": source.id,
            "pipeline": "structured-knowledge-extraction",
            "pipeline_version": PIPELINE_VERSION,
            "version": version,
            "run_id": run_id,
            "active": True,
        }
        created: list[DerivedArtifact] = []
        for draft, evidence in normalized:
            artifact = DerivedArtifact(
                owner_id=source.owner_id,
                kind=draft.kind,
                title=draft.title,
                content=draft.content,
                metadata_json=metadata_base.copy(),
            )
            self.session.add(artifact)
            self.session.flush()
            for chunk in evidence:
                self.session.add(
                    ArtifactSource(
                        artifact_id=artifact.id,
                        content_chunk_id=chunk.id,
                        source_role="supporting_evidence",
                        supporting_excerpt=chunk.text[:500],
                    )
                )
            self.session.add(
                ArtifactGeneration(
                    artifact_id=artifact.id,
                    provider=model_metadata.provider,
                    model=model_metadata.model,
                    model_version=model_metadata.model_version,
                    prompt_name=PROMPT_NAME,
                    prompt_version=PROMPT_VERSION,
                    confidence=draft.confidence,
                    metadata_json=model_metadata.as_dict(),
                )
            )
            self._persist_specialized_record(artifact, draft, evidence)
            created.append(artifact)

        created_ids = [artifact.id for artifact in created]
        for artifact in old_artifacts:
            artifact.metadata_json = {
                **artifact.metadata_json,
                "active": False,
                "superseded_by": created_ids,
                "superseded_at": datetime.now(UTC).isoformat(),
            }
        for artifact in created:
            artifact.metadata_json = {
                **artifact.metadata_json,
                "replaces": [old.id for old in old_artifacts],
            }
        return tuple(created)

    def _persist_specialized_record(
        self,
        artifact: DerivedArtifact,
        draft: ArtifactDraft,
        evidence: tuple[ContentChunk, ...],
    ) -> None:
        if draft.kind == "decision":
            self.session.add(Decision(artifact_id=artifact.id))
        elif draft.kind == "task":
            self.session.add(Task(artifact_id=artifact.id))
        elif draft.kind == "open_question":
            self.session.add(OpenQuestion(artifact_id=artifact.id))
        elif draft.kind == "idea":
            self.session.add(Idea(artifact_id=artifact.id))
        elif draft.kind == "classification":
            existing = self.session.scalars(
                select(KnowledgeObject).where(
                    KnowledgeObject.owner_id == artifact.owner_id,
                    KnowledgeObject.deleted_at.is_(None),
                )
            )
            label = draft.title or draft.content
            match = next(
                (item for item in existing if item.title.casefold() == label.casefold()), None
            )
            for chunk in evidence:
                self.session.add(
                    AIClassification(
                        owner_id=artifact.owner_id,
                        content_chunk_id=chunk.id,
                        knowledge_object_id=match.id if match else None,
                        artifact_id=artifact.id,
                        label=label,
                        confidence=draft.confidence or 0.0,
                    )
                )

    def _source_chunks(self, source: SourceFile) -> tuple[ContentChunk, ...]:
        document_chunks = tuple(
            self.session.scalars(
                select(ContentChunk)
                .join(Document, ContentChunk.document_id == Document.id)
                .where(
                    ContentChunk.owner_id == source.owner_id,
                    Document.source_file_id == source.id,
                    Document.deleted_at.is_(None),
                )
                .order_by(ContentChunk.sequence)
            )
        )
        if document_chunks:
            return document_chunks
        meeting = self.session.scalar(select(Meeting).where(Meeting.source_file_id == source.id))
        if meeting is None:
            return ()
        transcript = self.session.scalar(
            select(Transcript).where(Transcript.meeting_id == meeting.id)
        )
        if transcript is None:
            return ()
        segments = tuple(
            self.session.scalars(
                select(TranscriptSegment)
                .where(TranscriptSegment.transcript_id == transcript.id)
                .order_by(TranscriptSegment.sequence)
            )
        )
        chunks: list[ContentChunk] = []
        for segment in segments:
            chunk = self.session.scalar(
                select(ContentChunk).where(ContentChunk.transcript_segment_id == segment.id)
            )
            if chunk is None:
                chunk = ContentChunk(
                    owner_id=source.owner_id,
                    transcript_segment_id=segment.id,
                    sequence=segment.sequence,
                    text=segment.text,
                    source_start_ms=segment.start_ms,
                    source_end_ms=segment.end_ms,
                    location={"start_ms": segment.start_ms, "end_ms": segment.end_ms},
                )
                self.session.add(chunk)
                self.session.flush()
            chunks.append(chunk)
        return tuple(chunks)

    def _processing_job(self, source_file_id: int) -> ProcessingJob | None:
        return self.session.scalar(
            select(ProcessingJob)
            .where(
                ProcessingJob.subject_type == "source_file",
                ProcessingJob.subject_id == source_file_id,
            )
            .order_by(ProcessingJob.id.desc())
        )

    def _start_attempt(self, job: ProcessingJob) -> ProcessingAttempt:
        latest = self.session.scalar(
            select(func.max(ProcessingAttempt.attempt_number)).where(
                ProcessingAttempt.job_id == job.id
            )
        )
        attempt = ProcessingAttempt(
            job_id=job.id,
            attempt_number=(latest or 0) + 1,
            status="running",
            started_at=datetime.now(UTC),
        )
        self.session.add(attempt)
        self.session.flush()
        return attempt

    def _mark_failed(
        self,
        source: SourceFile,
        job: ProcessingJob,
        attempt: ProcessingAttempt | None,
        message: str,
    ) -> None:
        if attempt is not None:
            attempt.status = "failed"
            attempt.error_code = "KNOWLEDGE_EXTRACTION_ERROR"
            attempt.error_message = message
            attempt.finished_at = datetime.now(UTC)
        job.status = "failed"
        job.metadata_json = {**job.metadata_json, "stage": "failed", "error": message}
        self._set_status(source, "failed", 0.0)
        self.session.commit()

    @staticmethod
    def _set_status(source: SourceFile, status: str, progress: float) -> None:
        timeline = list(source.metadata_json.get("status_timeline", []))
        timeline.append({"status": status, "at": datetime.now(UTC).isoformat()})
        source.metadata_json = {
            **source.metadata_json,
            "status_timeline": timeline,
            "progress": progress,
        }
        source.ingestion_status = status


_SYSTEM_PROMPT = """You extract structured knowledge from source chunks.
Return only JSON matching the supplied schema. Never invent evidence: every
artifact must reference one or more exact source_chunk_ids from the input.
Create concise and detailed summaries when supported by the source, and add
decisions, tasks, open questions, important statements, risks, ideas, and
topic/project classifications only when the source supports them. Use
classification titles for topic or project labels. Keep original wording out
of generated content unless it is an important statement, and keep each
artifact useful and specific. Confidence is between 0 and 1.
"""
