from django.db import models

from apps.tenants.models import OrgOwnedModel

from .crypto import decrypt_dict, encrypt_dict


class Connection(OrgOwnedModel):
    """
    One configured link to one vendor account, e.g. "Google Workspace - acme.com".

    Non-secret settings live in `config` (plain JSON, safe to show in the UI).
    Secrets live in `encrypted_credentials` and are never serialised back out.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending setup"
        CONNECTED = "connected", "Connected"
        ERROR = "error", "Error"
        DISABLED = "disabled", "Disabled"

    provider = models.CharField(max_length=50)
    display_name = models.CharField(max_length=200)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    config = models.JSONField(default=dict, blank=True)
    encrypted_credentials = models.TextField(blank=True)
    sync_enabled = models.BooleanField(default=True)
    sync_interval_hours = models.PositiveIntegerField(default=6)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)

    class Meta:
        ordering = ["provider", "display_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "provider", "display_name"],
                name="uniq_connection_per_org_provider_name",
            )
        ]

    def __str__(self) -> str:
        return f"{self.display_name} ({self.provider})"

    # --- credentials ---
    def set_credentials(self, data: dict) -> None:
        self.encrypted_credentials = encrypt_dict(data or {})

    def get_credentials(self) -> dict:
        return decrypt_dict(self.encrypted_credentials)

    @property
    def has_credentials(self) -> bool:
        return bool(self.encrypted_credentials)
