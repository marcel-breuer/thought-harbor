"""Celery entrypoint for queued source parsing."""

from sqlalchemy import select

from thoughtharbor.db.session import SessionFactory
from thoughtharbor.documents.processing import ParsingService
from thoughtharbor.domain.models import SourceFile
from thoughtharbor.storage.factory import get_storage
from thoughtharbor.transcription.service import TranscriptionService
from thoughtharbor.workers.celery_app import celery_app


@celery_app.task(name="thoughtharbor.process_source_file")  # type: ignore[untyped-decorator]
def process_source_file(source_file_id: int) -> bool:
    """Run the shared parsing service in a worker process."""

    with SessionFactory() as session:
        source = session.scalar(select(SourceFile).where(SourceFile.id == source_file_id))
        if source is None:
            return False
        storage = get_storage()
        result: object | None
        if source.metadata_json.get("source_type") == "audio":
            result = TranscriptionService(session, storage).process(source_file_id)
        else:
            result = ParsingService(session, storage).process(source_file_id)
    return result is not None
