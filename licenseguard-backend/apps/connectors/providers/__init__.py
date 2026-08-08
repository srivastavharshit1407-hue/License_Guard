"""Importing this package registers every connector with the registry."""
from . import (  # noqa: F401
    atlassian,
    google_workspace,
    manual,
    microsoft365,
    slack,
    zoom,
)
