"""
The connector contract.

Adding a new vendor to LicenseGuard means writing ONE class here that answers
two questions:

    fetch_license_pools()  -> what SKUs exist and how many seats are in use?
    fetch_assignments()    -> who holds those seats?

Everything downstream (syncing, alerting, the UI) is vendor-agnostic and gets
the new integration for free. That is the whole point of the abstraction: you
will add many vendors over time and you do not want to touch the sync engine
each time.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PoolData:
    """Normalised licence pool coming back from any vendor."""

    external_id: str
    name: str
    application_name: str
    used_seats: int
    vendor: str = ""
    sku: str = ""
    total_seats: int | None = None  # None = vendor cannot tell us; keep the manual value
    category: str = "other"
    metadata: dict = field(default_factory=dict)


@dataclass
class AssignmentData:
    """Normalised seat holder."""

    user_email: str
    user_name: str = ""
    external_id: str = ""
    status: str = "active"
    assigned_at: datetime | None = None
    last_active_at: datetime | None = None


class ConnectorError(Exception):
    """Raised when a vendor call fails in a way the user should see."""


class BaseConnector(ABC):
    # --- describe yourself to the UI ---
    provider: str = ""
    label: str = ""
    description: str = ""
    docs_url: str = ""
    # Fields the user must fill in when creating the connection.
    # secret=True fields are encrypted; the rest go in Connection.config.
    config_fields: list[dict] = []
    supports_total_seats: bool = False

    def __init__(self, connection):
        self.connection = connection
        self.config = connection.config or {}
        self.credentials = connection.get_credentials() if connection.has_credentials else {}

    # --- the contract ---
    @abstractmethod
    def test_connection(self) -> dict:
        """Cheap call proving the credentials work. Raise ConnectorError if not."""

    @abstractmethod
    def fetch_license_pools(self) -> list[PoolData]:
        """Return every licence pool visible in this vendor account."""

    def fetch_assignments(self, pool: PoolData) -> list[AssignmentData]:
        """Optional: return the individual seat holders for one pool."""
        return []
