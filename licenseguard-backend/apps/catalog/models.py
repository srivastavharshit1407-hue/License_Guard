from django.db import models

from apps.tenants.models import OrgOwnedModel


class Application(OrgOwnedModel):
    """
    A product your company pays for: Google Workspace, Slack, Zoom, Jira...
    This is Tab 1 - the catalogue of everything you hold licences for.
    """

    class Category(models.TextChoices):
        PRODUCTIVITY = "productivity", "Productivity"
        COMMUNICATION = "communication", "Communication"
        DEVELOPMENT = "development", "Development"
        SECURITY = "security", "Security"
        DESIGN = "design", "Design"
        SALES_MARKETING = "sales_marketing", "Sales & Marketing"
        FINANCE = "finance", "Finance & HR"
        INFRASTRUCTURE = "infrastructure", "Infrastructure"
        OTHER = "other", "Other"

    name = models.CharField(max_length=200)
    vendor = models.CharField(max_length=200, blank=True)
    category = models.CharField(max_length=40, choices=Category.choices, default=Category.OTHER)
    description = models.TextField(blank=True)
    website = models.URLField(blank=True)
    logo_url = models.URLField(blank=True)
    owner_email = models.EmailField(blank=True, help_text="Internal person accountable for this app.")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "name"], name="uniq_application_name_per_org"
            )
        ]

    def __str__(self) -> str:
        return self.name

    # --- rollups across every licence pool attached to this application ---
    @property
    def total_seats(self) -> int:
        return sum(pool.total_seats for pool in self.license_pools.all())

    @property
    def used_seats(self) -> int:
        return sum(pool.used_seats for pool in self.license_pools.all())

    @property
    def utilization_pct(self) -> float:
        total = self.total_seats
        return round(self.used_seats / total * 100, 1) if total else 0.0
