"""
The sync engine.

One function, `sync_connection`, does the same thing for every vendor because
connectors all speak the same PoolData/AssignmentData language:

    connector -> PoolData[] -> upsert Application -> upsert LicensePool
              -> AssignmentData[] -> replace LicenseAssignment rows
              -> evaluate alert rules

`total_seats` rule: only overwrite it when the vendor genuinely knows the
purchased count (PoolData.total_seats is not None). Otherwise leave the number
the human typed in alone - clobbering it with an assigned-seat count would make
utilisation permanently read 100%.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone

from apps.catalog.models import Application
from apps.licenses.models import LicenseAssignment, LicensePool, SyncRun

from .base import ConnectorError
from .models import Connection
from .registry import build_connector

logger = logging.getLogger(__name__)


def sync_connection(connection: Connection) -> SyncRun:
    run = SyncRun.objects.create(organization=connection.organization, connection=connection)
    try:
        connector = build_connector(connection)
        pools = connector.fetch_license_pools()

        created = updated = assignments_synced = 0
        seen_pool_ids = set()
        for pool_data in pools:
            pool, was_created = _upsert_pool(connection, pool_data)
            seen_pool_ids.add(pool.pk)
            created += was_created
            updated += not was_created
            try:
                assignments_synced += _sync_assignments(
                    connection, pool, connector.fetch_assignments(pool_data)
                )
            except Exception as exc:  # assignment detail is best-effort
                logger.warning("Assignment sync failed for %s: %s", pool, exc)

        # Remove pools this connection used to report but no longer does (e.g.
        # a cancelled SKU, or leftovers from an earlier demo-mode sync). Only
        # when the fetch actually returned something - an empty `pools` list
        # is more likely a hidden connector error than "you now have zero
        # licenses", and we should never wipe real data on that ambiguity.
        if pools:
            stale = LicensePool.objects.filter(
                organization=connection.organization, source=connection.provider
            ).exclude(pk__in=seen_pool_ids)
            if stale.exists():
                logger.info("Removing %d stale pool(s) for connection %s", stale.count(), connection.pk)
                stale.delete()

        connection.status = Connection.Status.CONNECTED
        connection.last_sync_at = timezone.now()
        connection.last_error = ""
        connection.save(update_fields=["status", "last_sync_at", "last_error"])

        run.mark_success(
            pools_created=created,
            pools_updated=updated,
            assignments_synced=assignments_synced,
        )

        # Fresh numbers, so re-check the thresholds immediately.
        from apps.alerts.services import evaluate_rules_for_organization
        evaluate_rules_for_organization(connection.organization)

    except (ConnectorError, Exception) as exc:
        logger.exception("Sync failed for connection %s", connection.pk)
        connection.status = Connection.Status.ERROR
        connection.last_error = str(exc)[:2000]
        connection.save(update_fields=["status", "last_error"])
        run.mark_failed(exc)
    return run


@transaction.atomic
def _upsert_pool(connection: Connection, data) -> tuple[LicensePool, bool]:
    org = connection.organization

    application, _ = Application.objects.get_or_create(
        organization=org,
        name=data.application_name,
        defaults={"vendor": data.vendor, "category": data.category},
    )

    # Match on external_id first (survives renames), then fall back to name.
    pool = LicensePool.objects.filter(
        organization=org, application=application, external_id=data.external_id
    ).first() if data.external_id else None
    if pool is None:
        pool = LicensePool.objects.filter(
            organization=org, application=application, name=data.name
        ).first()

    was_created = pool is None
    if was_created:
        pool = LicensePool(organization=org, application=application, name=data.name)

    pool.external_id = data.external_id or pool.external_id
    pool.sku = data.sku or pool.sku
    pool.source = connection.provider
    pool.used_seats = data.used_seats
    if data.total_seats is not None:
        pool.total_seats = data.total_seats
        pool.total_seats_is_synced = True
    pool.last_synced_at = timezone.now()
    pool.save()
    return pool, was_created


@transaction.atomic
def _sync_assignments(connection: Connection, pool: LicensePool, assignments) -> int:
    if not assignments:
        return 0

    org = connection.organization
    seen_emails = set()
    for item in assignments:
        email = (item.user_email or "").strip().lower()
        if not email or "@" not in email:
            continue
        seen_emails.add(email)
        LicenseAssignment.objects.update_or_create(
            pool=pool,
            user_email=email,
            defaults={
                "organization": org,
                "user_name": item.user_name,
                "external_id": item.external_id,
                "status": item.status,
                "assigned_at": item.assigned_at,
                "last_active_at": item.last_active_at,
            },
        )

    # Anyone who disappeared from the vendor no longer holds a seat.
    pool.assignments.exclude(user_email__in=seen_emails).delete()
    return len(seen_emails)
