from django.db import models
from django.utils import timezone

from apps.tenants.models import OrgOwnedModel


class AlertRule(OrgOwnedModel):
    """
    Tab 3. "If Google Workspace goes past 90 seats, email ops@acme.com."

    Scope decides WHAT is watched, condition + threshold decide WHEN it fires,
    and cooldown_hours stops it firing every hour until someone fixes it.
    """

    class Scope(models.TextChoices):
        ALL_POOLS = "all_pools", "Every licence pool"
        APPLICATION = "application", "One application"
        POOL = "pool", "One licence pool"

    class Condition(models.TextChoices):
        UTILIZATION_ABOVE = "utilization_above", "Utilisation % is above"
        USED_SEATS_ABOVE = "used_seats_above", "Used seats are above"
        AVAILABLE_SEATS_BELOW = "available_seats_below", "Available seats are below"
        RENEWAL_WITHIN_DAYS = "renewal_within_days", "Renewal is within (days)"

    name = models.CharField(max_length=200)
    scope = models.CharField(max_length=20, choices=Scope.choices, default=Scope.ALL_POOLS)
    application = models.ForeignKey(
        "catalog.Application", on_delete=models.CASCADE,
        null=True, blank=True, related_name="alert_rules",
    )
    license_pool = models.ForeignKey(
        "licenses.LicensePool", on_delete=models.CASCADE,
        null=True, blank=True, related_name="alert_rules",
    )
    condition = models.CharField(
        max_length=30, choices=Condition.choices, default=Condition.UTILIZATION_ABOVE
    )
    threshold = models.FloatField(help_text="e.g. 90 for '90% utilised' or '90 seats'.")
    recipients = models.JSONField(
        default=list, help_text='Email addresses, e.g. ["ops@acme.com", "it@acme.com"]'
    )
    cooldown_hours = models.PositiveIntegerField(
        default=24, help_text="Minimum gap between two emails for the same pool + rule."
    )
    is_active = models.BooleanField(default=True)
    last_triggered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name

    def matches(self, pool) -> bool:
        """Is this pool in scope for this rule?"""
        if self.scope == self.Scope.POOL:
            return self.license_pool_id == pool.id
        if self.scope == self.Scope.APPLICATION:
            return self.application_id == pool.application_id
        return True

    #: Conditions that are meaningless until someone has entered the seat cap.
    CAPACITY_CONDITIONS = {"utilization_above", "available_seats_below"}

    def evaluate(self, pool) -> tuple[bool, float]:
        """Returns (breached, observed_value)."""
        # A pool with total_seats = 0 has not had its cap entered yet (common for
        # Google Workspace, which cannot supply it). Capacity rules would then
        # report "0 seats available" for every such pool and spam the recipients,
        # so stay quiet until the cap is known.
        if self.condition in self.CAPACITY_CONDITIONS and not pool.total_seats:
            return False, 0.0

        if self.condition == self.Condition.UTILIZATION_ABOVE:
            value = pool.utilization_pct
            return value > self.threshold, value
        if self.condition == self.Condition.USED_SEATS_ABOVE:
            value = float(pool.used_seats)
            return value > self.threshold, value
        if self.condition == self.Condition.AVAILABLE_SEATS_BELOW:
            value = float(pool.available_seats)
            return value < self.threshold, value
        if self.condition == self.Condition.RENEWAL_WITHIN_DAYS:
            if not pool.renewal_date:
                return False, 0.0
            days = (pool.renewal_date - timezone.now().date()).days
            return 0 <= days <= self.threshold, float(days)
        return False, 0.0

    def describe(self, pool, value: float) -> str:
        label = dict(self.Condition.choices)[self.condition]
        return f"{pool} - {label} {self.threshold:g} (currently {value:g})"


class AlertEvent(OrgOwnedModel):
    """Every time a rule fired. Also the cooldown ledger."""

    rule = models.ForeignKey(AlertRule, on_delete=models.CASCADE, related_name="events")
    license_pool = models.ForeignKey(
        "licenses.LicensePool", on_delete=models.CASCADE, related_name="alert_events"
    )
    triggered_at = models.DateTimeField(auto_now_add=True)
    observed_value = models.FloatField(default=0)
    message = models.TextField()
    recipients = models.JSONField(default=list)
    email_sent = models.BooleanField(default=False)
    email_error = models.TextField(blank=True)
    acknowledged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-triggered_at"]

    def __str__(self) -> str:
        return f"{self.rule.name} @ {self.triggered_at:%Y-%m-%d %H:%M}"
