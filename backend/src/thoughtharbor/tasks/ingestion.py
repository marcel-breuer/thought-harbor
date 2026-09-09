"""Celery entrypoint for queued source parsing."""

import logging

from sqlalchemy import select

from thoughtharbor.db.session import SessionFactory
from thoughtharbor.diarization.service import DiarizationService
from thoughtharbor.documents.processing import ParsingService
from thoughtharbor.domain.models import SourceFile
from thoughtharbor.knowledge.extraction import KnowledgeExtractionService
from thoughtharbor.search.service import SearchIndexService
from thoughtharbor.storage.factory import get_storage
from thoughtharbor.transcription.service import TranscriptionService
from thoughtharbor.workers.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="thoughtharbor.process_source_file",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)  # type: ignore[untyped-decorator]
def process_source_file(source_file_id: int) -> bool:
    """Run the shared parsing service in a worker process."""

    logger.info("processing source file", extra={"job_id": source_file_id})
    with SessionFactory() as session:
        source = session.scalar(select(SourceFile).where(SourceFile.id == source_file_id))
        if source is None:
            return False
        storage = get_storage()
        result: object | None
        if source.metadata_json.get("source_type") == "audio":
            result = TranscriptionService(session, storage).process(source_file_id)
            if result is not None:
                DiarizationService(session, storage).process(result.meeting_id)
        else:
            result = ParsingService(session, storage).process(source_file_id)
        if result is None:
            return False
        artifacts = KnowledgeExtractionService(session).process(source_file_id)
        if artifacts is None:
            return False
        SearchIndexService(session).enqueue_source(source_file_id)
    return True
