"""Provider name -> connector class. Populated by the @register decorator."""
from __future__ import annotations

from .base import BaseConnector

_REGISTRY: dict[str, type[BaseConnector]] = {}


def register(cls: type[BaseConnector]) -> type[BaseConnector]:
    if not cls.provider:
        raise ValueError(f"{cls.__name__} must define a `provider` string.")
    _REGISTRY[cls.provider] = cls
    return cls


def get_connector_class(provider: str) -> type[BaseConnector]:
    try:
        return _REGISTRY[provider]
    except KeyError:
        raise KeyError(f"No connector registered for provider '{provider}'.") from None


def build_connector(connection) -> BaseConnector:
    return get_connector_class(connection.provider)(connection)


def available_providers() -> list[dict]:
    return [
        {
            "provider": cls.provider,
            "label": cls.label,
            "description": cls.description,
            "docs_url": cls.docs_url,
            "config_fields": cls.config_fields,
            "supports_total_seats": cls.supports_total_seats,
        }
        for cls in sorted(_REGISTRY.values(), key=lambda c: c.label)
    ]
