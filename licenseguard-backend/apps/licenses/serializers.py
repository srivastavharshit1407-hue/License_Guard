from rest_framework import serializers

from apps.catalog.models import Application

from .models import LicenseAssignment, LicensePool, SyncRun


class LicensePoolSerializer(serializers.ModelSerializer):
    application_name = serializers.CharField(source="application.name", read_only=True)
    application_vendor = serializers.CharField(source="application.vendor", read_only=True)
    available_seats = serializers.IntegerField(read_only=True)
    utilization_pct = serializers.FloatField(read_only=True)
    is_over_capacity = serializers.BooleanField(read_only=True)
    annual_cost = serializers.FloatField(read_only=True)
    wasted_annual_cost = serializers.FloatField(read_only=True)

    class Meta:
        model = LicensePool
        fields = (
            "id", "application", "application_name", "application_vendor",
            "name", "sku", "external_id", "source",
            "total_seats", "used_seats", "total_seats_is_synced",
            "available_seats", "utilization_pct", "is_over_capacity",
            "unit_cost", "currency", "billing_cycle", "annual_cost", "wasted_annual_cost",
            "renewal_date", "notes", "last_synced_at", "is_active",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "last_synced_at", "created_at", "updated_at")

    def validate_application(self, value: Application) -> Application:
        request = self.context.get("request")
        if request and value.organization_id != request.user.organization_id:
            raise serializers.ValidationError("That application belongs to another organization.")
        return value


class LicenseAssignmentSerializer(serializers.ModelSerializer):
    pool_name = serializers.CharField(source="pool.name", read_only=True)
    application_name = serializers.CharField(source="pool.application.name", read_only=True)
    idle_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = LicenseAssignment
        fields = (
            "id", "pool", "pool_name", "application_name", "user_email", "user_name",
            "status", "assigned_at", "last_active_at", "idle_days", "created_at",
        )
        read_only_fields = fields


class SyncRunSerializer(serializers.ModelSerializer):
    provider = serializers.CharField(source="connection.provider", read_only=True)
    connection_name = serializers.CharField(source="connection.display_name", read_only=True)

    class Meta:
        model = SyncRun
        fields = (
            "id", "connection", "connection_name", "provider", "status",
            "started_at", "finished_at", "pools_created", "pools_updated",
            "assignments_synced", "error_message",
        )
        read_only_fields = fields


class CSVImportSerializer(serializers.Serializer):
    """
    For the many vendors with no usable API. Expected columns:
      application,vendor,pool_name,sku,total_seats,used_seats,unit_cost,currency,renewal_date
    """

    file = serializers.FileField()
