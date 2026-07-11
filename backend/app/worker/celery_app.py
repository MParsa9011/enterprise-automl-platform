"""Celery application.

The API enqueues training jobs onto this queue; a separate worker process
(``celery -A app.worker.celery_app worker``) consumes them. Training is CPU-bound
and can run for minutes, so it must never execute inside a request — offloading it
keeps the API responsive and lets training scale horizontally by adding workers.
"""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "automl",
    broker=str(settings.CELERY_BROKER_URL),
    backend=str(settings.CELERY_RESULT_BACKEND),
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    result_expires=60 * 60 * 24,  # keep results for a day
    task_default_queue="training",
)
