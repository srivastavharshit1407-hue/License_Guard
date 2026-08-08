from django.db import models
from django.utils import timezone

from apps.catalog.models import Application
from apps.tenants.models import OrgOwnedModel


class LicensePool(OrgOwnedModel):
    """
    A block of seats you bought for one SKU of one application.

    "Google Workspace Business Standard - 100 seats, 87 used" is one pool.
    This is Tab 2 - the licence cap and how much of it is consumed.

    Why `total_seats` is manual by default: most vendor APIs will happily tell
    you how many seats are ASSIGNED, but very few expose how many you PURCHASED
    (that number lives in a contract or reseller portal). So we sync `used_seats`
    automatically and let you type `total_seats` in - unless a connector can
    genuinely supply it, in which case it sets `total_seats_is_synced=True`.
    """

    class Source(models.TextChoices):
        MANUAL = "manual", "Manual entry"
        CSV = "csv", "CSV import"
        GOOGLE_WORKSPACE = "google_workspace", "Google Workspace"
        MICROSOFT_365 = "microsoft_365", "Microsoft 365"
        SLACK = "slack", "Slack"
        ZOOM = "zoom", "Zoom"
        ATLASSIAN = "atlassian", "Atlassian"

    application = models.ForeignKey(
        Application, on_delete=models.CASCADE, related_name="license_pools"
    )
    name = models.CharField(max_length=200, help_text="e.g. Business Standard")
    sku = models.CharField(max_length=200, blank=True)
    external_id = models.CharField(
        max_length=255, blank=True, help_text="Vendor-side identifier used to match on sync."
    )
    source = models.CharField(max_length=40, choices=Source.choices, default=Source.MANUAL)

    total_seats = models.PositiveIntegerField(default=0, help_text="Seats purchased (the cap).")
    used_seats = models.PositiveIntegerField(default=0, help_text="Seats currently assigned.")
    total_seats_is_synced = models.BooleanField(
        default=False,
        help_text="True when the vendor API supplies the purchased-seat count itself.",
    )

    unit_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, help_text="Cost per seat per billing period."
    )
    currency = models.CharField(max_length=3, default="USD")
    billing_cycle = models.CharField(
        max_length=20,
        choices=[("monthly", "Monthly"), ("annual", "Annual")],
        default="annual",
    )
    renewal_date = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    last_synced_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["application__name", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "application", "name"],
                name="uniq_pool_name_per_application",
            )
        ]

    def __str__(self) -> str:
        return f"{self.application.name} - {self.name}"

    @property
    def available_seats(self) -> int:
        return max(self.total_seats - self.used_seats, 0)

    @property
    def utilization_pct(self) -> float:
        return round(self.used_seats / self.total_seats * 100, 1) if self.total_seats else 0.0

    @property
    def is_over_capacity(self) -> bool:
        return self.total_seats > 0 and self.used_seats > self.total_seats

    @property
    def annual_cost(self) -> float:
        multiplier = 12 if self.billing_cycle == "monthly" else 1
        return float(self.unit_cost) * self.total_seats * multiplier

    @property
    def wasted_annual_cost(self) -> float:
        """What you are paying for seats nobody is using."""
        multiplier = 12 if self.billing_cycle == "monthly" else 1
        return float(self.unit_cost) * self.available_seats * multiplier


class LicenseAssignment(OrgOwnedModel):
    """One seat, held by one person. Populated by connectors on each sync."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        SUSPENDED = "suspended", "Suspended"
        REVOKED = "revoked", "Revoked"

    pool = models.ForeignKey(LicensePool, on_delete=models.CASCADE, related_name="assignments")
    user_email = models.EmailField()
    user_name = models.CharField(max_length=200, blank=True)
    external_id = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    assigned_at = models.DateTimeField(null=True, blank=True)
    last_active_at = models.DateTimeField(
        null=True, blank=True, help_text="Last sign-in. Powers 'reclaim idle seats'."
    )

    class Meta:
        ordering = ["user_email"]
        constraints = [
            models.UniqueConstraint(
                fields=["pool", "user_email"], name="uniq_assignment_per_pool_user"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_email} -> {self.pool}"

    @property
    def idle_days(self) -> int | None:
        if not self.last_active_at:
            return None
        return (timezone.now() - self.last_active_at).days


class SyncRun(OrgOwnedModel):
    """Audit trail: every attempt to pull data from a vendor."""

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"

    connection = models.ForeignKey(
        "connectors.Connection", on_delete=models.CASCADE, related_name="sync_runs"
    )
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    pools_created = models.PositiveIntegerField(default=0)
    pools_updated = models.PositiveIntegerField(default=0)
    assignments_synced = models.PositiveIntegerField(default=0)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.connection} @ {self.started_at:%Y-%m-%d %H:%M} ({self.status})"

    def mark_success(self, **counts):
        self.status = self.Status.SUCCESS
        self.finished_at = timezone.now()
        for key, value in counts.items():
            setattr(self, key, value)
        self.save()

    def mark_failed(self, message: str):
        self.status = self.Status.FAILED
        self.finished_at = timezone.now()
        self.error_message = str(message)[:5000]
        self.save()
