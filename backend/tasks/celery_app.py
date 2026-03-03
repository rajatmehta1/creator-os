"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "creator_os",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "poll-trends-every-2-hours": {
        "task": "tasks.trend_polling.poll_trends",
        "schedule": crontab(minute=0, hour="*/2"),
    },
    "sync-analytics-every-6-hours": {
        "task": "tasks.analytics_sync.sync_all_analytics",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "rebuild-dna-weekly": {
        "task": "tasks.dna_rebuild.rebuild_all_dna",
        "schedule": crontab(minute=0, hour=3, day_of_week=0),  # Sunday 3 AM
    },
}

# Auto-discover tasks
celery_app.autodiscover_tasks(["tasks"])
