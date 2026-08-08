from django.db.models import F, FloatField, Sum
from django.db.models.functions import Cast
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.tenants.mixins import OrgScopedMixin

from .csv_import import import_license_csv
from .models import LicenseAssignment, LicensePool, SyncRun
from .serializers import (
    CSVImportSerializer,
    LicenseAssignmentSerializer,
    LicensePoolSerializer,
    SyncRunSerializer,
)


class LicensePoolViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Tab 2 - licence caps and utilisation."""

    queryset = LicensePool.objects.select_related("application").all()
    serializer_class = LicensePoolSerializer
    filterset_fields = ["application", "source", "is_active", "currency"]
    search_fields = ["name", "sku", "application__name"]
    ordering_fields = ["name", "total_seats", "used_seats", "renewal_date"]

    @action(detail=True, methods=["get"])
    def assignments(self, request, pk=None):
        pool = self.get_object()
        qs = pool.assignments.all()
        page = self.paginate_queryset(qs)
        serializer = LicenseAssignmentSerializer(page or qs, many=True)
        return self.get_paginated_response(serializer.data) if page is not None \
            else Response(serializer.data)


class LicenseAssignmentViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = LicenseAssignment.objects.select_related("pool", "pool__application").all()
    serializer_class = LicenseAssignmentSerializer
    filterset_fields = ["pool", "status", "pool__application"]
    search_fields = ["user_email", "user_name"]
    ordering_fields = ["user_email", "last_active_at"]


class SyncRunViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = SyncRun.objects.select_related("connection").all()
    serializer_class = SyncRunSerializer
    filterset_fields = ["connection", "status"]


class DashboardSummaryView(OrgScopedMixin, APIView):
    """Numbers for the cards at the top of the dashboard."""

    def get(self, request):
        org = self.get_organization()
        pools = LicensePool.objects.filter(organization=org, is_active=True)

        # Aggregate aliases must not collide with the field names they sum,
        # hence the sum_ prefix - Django raises FieldError otherwise.
        totals = pools.aggregate(
            sum_total_seats=Sum("total_seats"),
            sum_used_seats=Sum("used_seats"),
            sum_annual_spend=Sum(Cast(F("unit_cost") * F("total_seats"), FloatField())),
        )
        total_seats = totals["sum_total_seats"] or 0
        used_seats = totals["sum_used_seats"] or 0

        at_risk = [
            {
                "id": p.id,
                "application": p.application.name,
                "pool": p.name,
                "used_seats": p.used_seats,
                "total_seats": p.total_seats,
                "utilization_pct": p.utilization_pct,
            }
            for p in pools.select_related("application")
            if p.total_seats and p.utilization_pct >= 85
        ]

        return Response({
            "application_count": org.applications.filter(is_active=True).count(),
            "pool_count": pools.count(),
            "total_seats": total_seats,
            "used_seats": used_seats,
            "available_seats": max(total_seats - used_seats, 0),
            "utilization_pct": round(used_seats / total_seats * 100, 1) if total_seats else 0.0,
            "estimated_annual_spend": round(totals["sum_annual_spend"] or 0, 2),
            "wasted_annual_spend": round(sum(p.wasted_annual_cost for p in pools), 2),
            "pools_at_risk": sorted(at_risk, key=lambda x: -x["utilization_pct"])[:10],
        })


class CSVImportView(OrgScopedMixin, APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = CSVImportSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            result = import_license_csv(
                self.get_organization(), serializer.validated_data["file"]
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)
