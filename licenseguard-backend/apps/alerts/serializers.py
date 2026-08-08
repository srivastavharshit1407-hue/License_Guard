from rest_framework import serializers

from .models import AlertEvent, AlertRule


class AlertRuleSerializer(serializers.ModelSerializer):
    application_name = serializers.CharField(source="application.name", read_only=True)
    pool_name = serializers.CharField(source="license_pool.name", read_only=True)
    event_count = serializers.SerializerMethodField()

    class Meta:
        model = AlertRule
        fields = (
            "id", "name", "scope", "application", "application_name",
            "license_pool", "pool_name", "condition", "threshold", "recipients",
            "cooldown_hours", "is_active", "last_triggered_at", "event_count",
            "created_at", "updated_at",
        )
        read_only_fields = ("id", "last_triggered_at", "created_at", "updated_at")

    def get_event_count(self, obj) -> int:
        return obj.events.count()

    def validate_recipients(self, value):
        if not isinstance(value, list) or not value:
            raise serializers.ValidationError("Add at least one recipient email address.")
        for email in value:
            if "@" not in str(email):
                raise serializers.ValidationError(f"'{email}' is not a valid email address.")
        return [str(e).strip().lower() for e in value]

    def validate(self, attrs):
        scope = attrs.get("scope", getattr(self.instance, "scope", AlertRule.Scope.ALL_POOLS))
        if scope == AlertRule.Scope.APPLICATION and not attrs.get(
            "application", getattr(self.instance, "application", None)
        ):
            raise serializers.ValidationError({"application": "Required when scope is 'application'."})
        if scope == AlertRule.Scope.POOL and not attrs.get(
            "license_pool", getattr(self.instance, "license_pool", None)
        ):
            raise serializers.ValidationError({"license_pool": "Required when scope is 'pool'."})
        return attrs


class AlertEventSerializer(serializers.ModelSerializer):
    rule_name = serializers.CharField(source="rule.name", read_only=True)
    pool_name = serializers.CharField(source="license_pool.name", read_only=True)
    application_name = serializers.CharField(
        source="license_pool.application.name", read_only=True
    )

    class Meta:
        model = AlertEvent
        fields = (
            "id", "rule", "rule_name", "license_pool", "pool_name", "application_name",
            "triggered_at", "observed_value", "message", "recipients",
            "email_sent", "email_error", "acknowledged_at",
        )
        read_only_fields = fields
