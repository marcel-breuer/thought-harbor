"""Celery entrypoint for queued source parsing."""

from thoughtharbor.db.session import SessionFactory
from thoughtharbor.documents.processing import ParsingService
from thoughtharbor.storage.factory import get_storage
from thoughtharbor.workers.celery_app import celery_app


@celery_app.task(name="thoughtharbor.process_source_file")  # type: ignore[untyped-decorator]
def process_source_file(source_file_id: int) -> bool:
    """Run the shared parsing service in a worker process."""

    with SessionFactory() as session:
        result = ParsingService(session, get_storage()).process(source_file_id)
    return result is not None
