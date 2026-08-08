from django.apps import AppConfig


class ConnectorsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.connectors"

    def ready(self):
        # Importing the providers package registers every connector class.
        from . import providers  # noqa: F401
