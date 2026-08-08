"""
Manual connector.

Plenty of vendors have no usable API, or one locked behind an enterprise tier.
This connector exists so those licences still live in the same tables, feed the
same dashboard and trigger the same alerts as the automated ones - you just
update the numbers yourself (or via the CSV importer).
"""
from __future__ import annotations

from ..base import BaseConnector, PoolData
from ..registry import register


@register
class ManualConnector(BaseConnector):
    provider = "manual"
    label = "Manual / CSV"
    description = "For vendors without an API. Enter seats by hand or import a CSV."
    docs_url = ""
    supports_total_seats = True
    config_fields = [
        {"key": "note", "label": "Note", "type": "text", "required": False, "secret": False},
    ]

    def test_connection(self) -> dict:
        return {"ok": True, "message": "Manual source - nothing to test."}

    def fetch_license_pools(self) -> list[PoolData]:
        return []
