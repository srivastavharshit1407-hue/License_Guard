from rest_framework import serializers

from .models import Connection
from .registry import get_connector_class


class ConnectionSerializer(serializers.ModelSerializer):
    """
    `credentials` is write-only by design. Secrets go in, nothing comes back out.
    The UI shows `has_credentials` so it can render "Configured / Not configured".
    """

    credentials = serializers.DictField(write_only=True, required=False)
    has_credentials = serializers.BooleanField(read_only=True)
    provider_label = serializers.SerializerMethodField()

    class Meta:
        model = Connection
        fields = (
            "id", "provider", "provider_label", "display_name", "status",
            "config", "credentials", "has_credentials",
            "sync_enabled", "sync_interval_hours", "last_sync_at", "last_error",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "status", "last_sync_at", "last_error",
                            "created_at", "updated_at")

    def get_provider_label(self, obj) -> str:
        try:
            return get_connector_class(obj.provider).label
        except KeyError:
            return obj.provider

    def validate_provider(self, value: str) -> str:
        try:
            get_connector_class(value)
        except KeyError:
            raise serializers.ValidationError(f"Unknown provider '{value}'.") from None
        return value

    def create(self, validated_data):
        credentials = validated_data.pop("credentials", None)
        instance = super().create(validated_data)
        if credentials:
            instance.set_credentials(credentials)
            instance.save(update_fields=["encrypted_credentials"])
        return instance

    def update(self, instance, validated_data):
        credentials = validated_data.pop("credentials", None)
        instance = super().update(instance, validated_data)
        if credentials:
            instance.set_credentials(credentials)
            instance.save(update_fields=["encrypted_credentials"])
        return instance
