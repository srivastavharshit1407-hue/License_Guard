"""
Alert evaluation and delivery.

Called in two places:
  - right after a successful sync (so alerts feel instant), and
  - hourly by Celery beat (so manual edits and renewal dates get caught too).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone

from apps.licenses.models import LicensePool

from .models import AlertEvent, AlertRule

logger = logging.getLogger(__name__)


def evaluate_rules_for_organization(organization) -> list[AlertEvent]:
    pools = list(
        LicensePool.objects.filter(organization=organization, is_active=True)
        .select_related("application")
    )
    rules = AlertRule.objects.filter(organization=organization, is_active=True)

    fired: list[AlertEvent] = []
    for rule in rules:
        for pool in pools:
            if not rule.matches(pool):
                continue
            breached, value = rule.evaluate(pool)
            if not breached or _in_cooldown(rule, pool):
                continue

            event = AlertEvent.objects.create(
                organization=organization,
                rule=rule,
                license_pool=pool,
                observed_value=value,
                message=rule.describe(pool, value),
                recipients=rule.recipients or [],
            )
            _send_email(event)
            fired.append(event)

    if fired:
        AlertRule.objects.filter(pk__in={e.rule_id for e in fired}).update(
            last_triggered_at=timezone.now()
        )
    return fired


def _in_cooldown(rule: AlertRule, pool: LicensePool) -> bool:
    if not rule.cooldown_hours:
        return False
    cutoff = timezone.now() - timedelta(hours=rule.cooldown_hours)
    return AlertEvent.objects.filter(
        rule=rule, license_pool=pool, triggered_at__gte=cutoff
    ).exists()


def _send_email(event: AlertEvent) -> None:
    recipients = [r for r in (event.recipients or []) if r]
    if not recipients:
        event.email_error = "No recipients configured on this rule."
        event.save(update_fields=["email_error"])
        return

    pool = event.license_pool
    context = {
        "event": event,
        "rule": event.rule,
        "pool": pool,
        "application": pool.application,
        "organization": event.organization,
        "frontend_url": settings.FRONTEND_URL,
    }
    subject = f"[LicenseGuard] {pool.application.name} - {pool.name} needs attention"

    try:
        text_body = render_to_string("alerts/threshold_alert.txt", context)
        html_body = render_to_string("alerts/threshold_alert.html", context)
        message = EmailMultiAlternatives(
            subject, text_body, settings.DEFAULT_FROM_EMAIL, recipients
        )
        message.attach_alternative(html_body, "text/html")
        message.send(fail_silently=False)
        event.email_sent = True
    except Exception as exc:
        logger.exception("Failed to send alert email for event %s", event.pk)
        event.email_error = str(exc)[:1000]
    event.save(update_fields=["email_sent", "email_error"])
