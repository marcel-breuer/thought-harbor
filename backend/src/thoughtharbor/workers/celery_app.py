"""Shared Celery application entrypoint."""

import os

from celery import Celery

celery_app = Celery(
    "thoughtharbor",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)
celery_app.conf.update(
    accept_content=["json"],
    enable_utc=True,
    result_serializer="json",
    task_serializer="json",
    timezone="UTC",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True,
    worker_send_task_events=True,
    broker_transport_options={"visibility_timeout": 3600},
    result_expires=3600,
    imports=("thoughtharbor.tasks.ingestion", "thoughtharbor.tasks.search"),
)

# Register the shared task for both worker discovery and direct application imports.
from thoughtharbor.tasks.ingestion import process_source_file  # noqa: E402, F401
from thoughtharbor.tasks.search import index_source_content  # noqa: E402, F401
