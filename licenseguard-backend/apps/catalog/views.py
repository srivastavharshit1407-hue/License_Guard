from rest_framework import viewsets

from apps.tenants.mixins import OrgScopedMixin

from .models import Application
from .serializers import ApplicationSerializer


class ApplicationViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Tab 1 - every application the organization holds licences for."""

    queryset = Application.objects.prefetch_related("license_pools").all()
    serializer_class = ApplicationSerializer
    filterset_fields = ["category", "is_active", "vendor"]
    search_fields = ["name", "vendor", "description"]
    ordering_fields = ["name", "created_at"]
