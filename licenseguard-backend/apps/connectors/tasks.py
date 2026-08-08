"""Celery tasks. This is what makes LicenseGuard 'automatic' rather than a form."""
from __future__ import annotations

import logging

from celery import shared_task

from .models import Connection
from .services import sync_connection

logger = logging.getLogger(__name__)


@shared_task(name="apps.connectors.tasks.sync_connection_task")
def sync_connection_task(connection_id: int) -> dict:
    connection = Connection.objects.get(pk=connection_id)
    run = sync_connection(connection)
    return {
        "connection": connection_id,
        "status": run.status,
        "pools_created": run.pools_created,
        "pools_updated": run.pools_updated,
    }


@shared_task(name="apps.connectors.tasks.sync_all_connections")
def sync_all_connections() -> dict:
    queryset = Connection.objects.filter(sync_enabled=True).exclude(
        status=Connection.Status.DISABLED
    ).exclude(provider="manual")
    for connection in queryset:
        sync_connection_task.delay(connection.pk)
    return {"queued": queryset.count()}
