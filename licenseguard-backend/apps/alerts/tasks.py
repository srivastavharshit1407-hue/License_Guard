from celery import shared_task

from apps.tenants.models import Organization

from .services import evaluate_rules_for_organization


@shared_task(name="apps.alerts.tasks.evaluate_all_alert_rules")
def evaluate_all_alert_rules() -> dict:
    total = 0
    for organization in Organization.objects.filter(is_active=True):
        total += len(evaluate_rules_for_organization(organization))
    return {"alerts_fired": total}
