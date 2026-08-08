from django.contrib import admin

from .models import LicenseAssignment, LicensePool, SyncRun


@admin.register(LicensePool)
class LicensePoolAdmin(admin.ModelAdmin):
    list_display = (
        "application", "name", "source", "used_seats", "total_seats",
        "utilization_pct", "renewal_date", "last_synced_at",
    )
    list_filter = ("organization", "source", "is_active", "application")
    search_fields = ("name", "sku", "application__name")


@admin.register(LicenseAssignment)
class LicenseAssignmentAdmin(admin.ModelAdmin):
    list_display = ("user_email", "pool", "status", "last_active_at")
    list_filter = ("organization", "status", "pool")
    search_fields = ("user_email", "user_name")


@admin.register(SyncRun)
class SyncRunAdmin(admin.ModelAdmin):
    list_display = ("connection", "status", "started_at", "finished_at", "pools_updated")
    list_filter = ("organization", "status")
