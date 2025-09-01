from __future__ import annotations

from os import getenv

from celery.schedules import crontab

from api.config.application import TIME_ZONE

broker_url = getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
result_backend = getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

task_serializer = "json"
result_serializer = "json"
accept_content = ["json"]

task_always_eager = getenv("CELERY_TASK_ALWAYS_EAGER", "false").lower() == "true"
task_eager_propagates = getenv("CELERY_TASK_EAGER_PROPAGATES", "false").lower() == "true"
task_ignore_result = getenv("CELERY_TASK_IGNORE_RESULT", "false").lower() == "true"

timezone = TIME_ZONE
enable_utc = True

# Ensure Celery imports our top-level tasks package (not a Django app)
imports = (
    "tasks.daily",
)

# Daily schedule at 09:30 (project TIME_ZONE)
beat_schedule = {
    "send-daily-rates-0930": {
        "task": "tasks.daily.send_daily_rates",
        "schedule": crontab(minute=30, hour=9),
    },
}
