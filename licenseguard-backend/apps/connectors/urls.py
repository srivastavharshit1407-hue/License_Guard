from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import ConnectionViewSet, ProviderListView

router = DefaultRouter()
router.register("connections", ConnectionViewSet, basename="connection")

urlpatterns = router.urls + [
    path("connectors/providers/", ProviderListView.as_view(), name="connector-providers"),
]
