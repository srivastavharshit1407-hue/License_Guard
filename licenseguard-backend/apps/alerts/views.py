from django.utils import timezone
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.tenants.mixins import OrgScopedMixin

from .models import AlertEvent, AlertRule
from .serializers import AlertEventSerializer, AlertRuleSerializer
from .services import evaluate_rules_for_organization


class AlertRuleViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    """Tab 3 - thresholds and who gets emailed."""

    queryset = AlertRule.objects.select_related("application", "license_pool").all()
    serializer_class = AlertRuleSerializer
    filterset_fields = ["scope", "condition", "is_active"]
    search_fields = ["name"]

    @action(detail=False, methods=["post"])
    def evaluate(self, request):
        """Run every rule right now instead of waiting for the hourly job."""
        events = evaluate_rules_for_organization(self.get_organization())
        return Response({
            "triggered": len(events),
            "events": AlertEventSerializer(events, many=True).data,
        })


class AlertEventViewSet(OrgScopedMixin, viewsets.ReadOnlyModelViewSet):
    queryset = AlertEvent.objects.select_related(
        "rule", "license_pool", "license_pool__application"
    ).all()
    serializer_class = AlertEventSerializer
    filterset_fields = ["rule", "license_pool", "email_sent"]

    @action(detail=True, methods=["post"])
    def acknowledge(self, request, pk=None):
        event = self.get_object()
        event.acknowledged_at = timezone.now()
        event.save(update_fields=["acknowledged_at"])
        return Response(self.get_serializer(event).data)
