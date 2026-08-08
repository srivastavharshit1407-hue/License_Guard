from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.licenses.serializers import SyncRunSerializer
from apps.tenants.mixins import OrgScopedMixin

from .base import ConnectorError
from .models import Connection
from .registry import available_providers, build_connector
from .serializers import ConnectionSerializer
from .services import sync_connection


class ProviderListView(APIView):
    """What LicenseGuard can connect to, and which fields each one needs."""

    def get(self, request):
        return Response(available_providers())


class ConnectionViewSet(OrgScopedMixin, viewsets.ModelViewSet):
    queryset = Connection.objects.all()
    serializer_class = ConnectionSerializer
    filterset_fields = ["provider", "status", "sync_enabled"]
    search_fields = ["display_name", "provider"]

    @action(detail=True, methods=["post"])
    def test(self, request, pk=None):
        connection = self.get_object()
        try:
            result = build_connector(connection).test_connection()
        except (ConnectorError, Exception) as exc:
            return Response({"ok": False, "detail": str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)
        return Response(result)

    @action(detail=True, methods=["post"])
    def sync(self, request, pk=None):
        """
        Runs the sync inline so the UI gets an immediate answer. Swap the body
        for `sync_connection_task.delay(connection.pk)` once you have Celery
        running and want the request to return straight away.
        """
        run = sync_connection(self.get_object())
        return Response(SyncRunSerializer(run).data)
