from django.contrib import admin

from .models import Connection


@admin.register(Connection)
class ConnectionAdmin(admin.ModelAdmin):
    list_display = ("display_name", "organization", "provider", "status",
                    "sync_enabled", "last_sync_at")
    list_filter = ("organization", "provider", "status", "sync_enabled")
    readonly_fields = ("encrypted_credentials", "last_sync_at", "last_error")
