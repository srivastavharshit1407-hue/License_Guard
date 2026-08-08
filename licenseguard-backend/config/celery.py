import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("licenseguard")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

# Default schedule. django-celery-beat lets you edit these from the admin later.
app.conf.beat_schedule = {
    "sync-all-connections-every-6-hours": {
        "task": "apps.connectors.tasks.sync_all_connections",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "evaluate-alert-rules-hourly": {
        "task": "apps.alerts.tasks.evaluate_all_alert_rules",
        "schedule": crontab(minute=15),
    },
}
