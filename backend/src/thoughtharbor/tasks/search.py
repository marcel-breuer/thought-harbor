"""Celery tasks for queued semantic indexing."""

from datetime import UTC, datetime

from sqlalchemy import select

from thoughtharbor.db.session import SessionFactory
from thoughtharbor.domain.models import ProcessingJob
from thoughtharbor.search.service import SearchIndexService
from thoughtharbor.workers.celery_app import celery_app


@celery_app.task(
    name="thoughtharbor.index_source_content",
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)  # type: ignore[untyped-decorator]
def index_source_content(source_file_id: int) -> int:
    """Index one source in a worker and retain a durable job status."""

    with SessionFactory() as session:
        job = session.scalar(
            select(ProcessingJob)
            .where(
                ProcessingJob.job_type == "search_index",
                ProcessingJob.subject_type == "source_file",
                ProcessingJob.subject_id == source_file_id,
            )
            .order_by(ProcessingJob.id.desc())
        )
        if job is not None:
            job.status = "running"
            job.metadata_json = {**job.metadata_json, "stage": "embedding"}
            session.commit()
        try:
            count = SearchIndexService(session).index_source(source_file_id)
        except Exception as error:
            if job is not None:
                job.status = "failed"
                job.metadata_json = {
                    **job.metadata_json,
                    "stage": "failed",
                    "error": str(error),
                    "finished_at": datetime.now(UTC).isoformat(),
                }
                session.commit()
            raise
        if job is not None:
            job.status = "succeeded"
            job.metadata_json = {
                **job.metadata_json,
                "stage": "complete",
                "chunk_count": count,
                "finished_at": datetime.now(UTC).isoformat(),
            }
            session.commit()
        return count
