from django.contrib import admin

from .models import Application


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ("name", "organization", "vendor", "category", "is_active")
    list_filter = ("organization", "category", "is_active")
    search_fields = ("name", "vendor")
