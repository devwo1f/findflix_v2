from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "findflix",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
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
    result_expires=3600,
)

# Periodic tasks
celery_app.conf.beat_schedule = {
    "sync-trending-daily": {
        "task": "app.tasks.sync_tasks.sync_trending_titles",
        "schedule": crontab(hour=3, minute=0),  # 3 AM UTC daily
    },
    "sync-availability-daily": {
        "task": "app.tasks.sync_tasks.sync_availability",
        "schedule": crontab(hour=4, minute=0),  # 4 AM UTC daily
    },
    "update-embeddings-weekly": {
        "task": "app.tasks.sync_tasks.update_user_embeddings",
        "schedule": crontab(hour=5, minute=0, day_of_week="sunday"),
    },
}
