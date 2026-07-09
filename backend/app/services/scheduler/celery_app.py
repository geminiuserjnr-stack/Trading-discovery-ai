from celery import Celery
from celery.schedules import crontab
from backend.app.config.settings import settings

celery_app = Celery(
    "trading_discovery",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.set_default()

celery_app.conf.update(
    timezone="UTC",
    enable_utc=True,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)

# Auto-discover tasks from the tasks module
celery_app.autodiscover_tasks(["backend.app.services.scheduler"])

# Define Celery Beat Schedule
celery_app.conf.beat_schedule = {
    "run-search-queue-every-30-min": {
        "task": "backend.app.services.scheduler.tasks.run_search_queue",
        "schedule": crontab(minute="*/30"),
    },
    "refresh-active-channels-every-hour": {
        "task": "backend.app.services.scheduler.tasks.refresh_active_channels",
        "schedule": crontab(minute="0", hour="*"),
    },
    "generate-search-queries-daily": {
        "task": "backend.app.services.scheduler.tasks.generate_search_queries",
        "schedule": crontab(minute="0", hour="0"),
    },
    "recalculate-rankings-daily": {
        "task": "backend.app.services.scheduler.tasks.recalculate_rankings",
        "schedule": crontab(minute="0", hour="0"),
    },
    "cleanup-old-logs-daily": {
        "task": "backend.app.services.scheduler.tasks.cleanup_old_logs",
        "schedule": crontab(minute="0", hour="0"),
    },
    "update-statistics-daily": {
        "task": "backend.app.services.scheduler.tasks.update_statistics",
        "schedule": crontab(minute="0", hour="0"),
    },
}
