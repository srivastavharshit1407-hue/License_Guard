from rest_framework import serializers

from .models import Application


class ApplicationSerializer(serializers.ModelSerializer):
    total_seats = serializers.IntegerField(read_only=True)
    used_seats = serializers.IntegerField(read_only=True)
    utilization_pct = serializers.FloatField(read_only=True)
    pool_count = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = (
            "id", "name", "vendor", "category", "description", "website",
            "logo_url", "owner_email", "is_active",
            "total_seats", "used_seats", "utilization_pct", "pool_count",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def get_pool_count(self, obj) -> int:
        return obj.license_pools.count()
