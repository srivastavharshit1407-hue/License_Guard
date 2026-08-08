from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    CSVImportView,
    DashboardSummaryView,
    LicenseAssignmentViewSet,
    LicensePoolViewSet,
    SyncRunViewSet,
)

router = DefaultRouter()
router.register("license-pools", LicensePoolViewSet, basename="license-pool")
router.register("license-assignments", LicenseAssignmentViewSet, basename="license-assignment")
router.register("sync-runs", SyncRunViewSet, basename="sync-run")

# Order matters: these must come BEFORE router.urls, otherwise the router's
# detail route treats "import-csv" as a primary key and returns 405.
urlpatterns = [
    path("dashboard/summary/", DashboardSummaryView.as_view(), name="dashboard-summary"),
    path("license-pools/import-csv/", CSVImportView.as_view(), name="license-csv-import"),
] + router.urls
