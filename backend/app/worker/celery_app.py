"""Celery application for the CI platform (SPEC.md §6).

Broker and result backend both use Redis. Delivery/back-pressure settings
keep jobs safe: JSON serialisation, late acks, prefetch limit 1 (one job
per worker at a time), worker recycling, and broker retry on startup so a
temporary Redis outage does not kill the worker.
"""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

_settings = get_settings()

celery_app = Celery(
    "ci_worker",
    broker=_settings.redis_url,
    backend=_settings.redis_url,
    # Imported at worker startup so tasks register on this app instance.
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
    worker_max_tasks_per_child=100,
    broker_connection_retry_on_startup=True,
    broker_connection_max_retries=0,      # retry forever until broker is up
    result_expires=86400,                 # keep results for 24h
    task_default_queue="ci_jobs",
    task_default_exchange="ci_jobs",
    task_default_routing_key="ci_jobs",
    task_routes={
        "app.worker.tasks.execute_research_job": {"queue": "ci_jobs"},
    },
)