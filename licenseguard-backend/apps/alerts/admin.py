from django.contrib import admin

from .models import AlertEvent, AlertRule


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "scope", "condition", "threshold",
                    "is_active", "last_triggered_at")
    list_filter = ("organization", "scope", "condition", "is_active")


@admin.register(AlertEvent)
class AlertEventAdmin(admin.ModelAdmin):
    list_display = ("rule", "license_pool", "observed_value", "triggered_at", "email_sent")
    list_filter = ("organization", "email_sent")
