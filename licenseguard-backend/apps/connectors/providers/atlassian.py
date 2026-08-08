"""
Atlassian (Jira / Confluence) connector.

`GET /rest/api/3/applicationrole` on a Jira Cloud site returns, per application
role, `numberOfSeats` and `userCount` - both numbers, straight from the API.

SETUP
  1. id.atlassian.com -> Security -> Create API token.
  2. Note your site URL, e.g. https://acme.atlassian.net
  3. Auth is HTTP Basic: your email + the API token.
"""
from __future__ import annotations

import requests
from django.conf import settings

from ..base import BaseConnector, ConnectorError, PoolData
from ..registry import register


@register
class AtlassianConnector(BaseConnector):
    provider = "atlassian"
    label = "Atlassian (Jira / Confluence)"
    description = "Reads seats purchased and seats used per Atlassian application role."
    docs_url = "https://developer.atlassian.com/cloud/jira/platform/rest/v3/"
    supports_total_seats = True
    config_fields = [
        {"key": "site_url", "label": "Site URL", "type": "url", "required": True,
         "secret": False, "placeholder": "https://acme.atlassian.net"},
        {"key": "email", "label": "Atlassian account email", "type": "email",
         "required": True, "secret": False},
        {"key": "api_token", "label": "API token", "type": "password",
         "required": True, "secret": True},
    ]

    def _get(self, path: str):
        site = (self.config.get("site_url") or "").rstrip("/")
        response = requests.get(
            f"{site}{path}",
            auth=(self.config.get("email"), self.credentials.get("api_token")),
            headers={"Accept": "application/json"},
            timeout=60,
        )
        if response.status_code != 200:
            raise ConnectorError(f"Atlassian call {path} failed: {response.text[:300]}")
        return response.json()

    def test_connection(self) -> dict:
        if settings.CONNECTORS_DEMO_MODE:
            return {"ok": True, "demo": True}
        me = self._get("/rest/api/3/myself")
        return {"ok": True, "message": f"Authenticated as {me.get('emailAddress', 'unknown')}."}

    def fetch_license_pools(self) -> list[PoolData]:
        if settings.CONNECTORS_DEMO_MODE:
            return [
                PoolData(external_id="jira-software", name="Jira Software",
                         application_name="Atlassian", vendor="Atlassian",
                         category="development", used_seats=73, total_seats=100),
                PoolData(external_id="confluence", name="Confluence",
                         application_name="Atlassian", vendor="Atlassian",
                         category="development", used_seats=61, total_seats=100),
            ]

        return [
            PoolData(
                external_id=role.get("key", ""),
                name=role.get("name", role.get("key", "")),
                application_name="Atlassian",
                vendor="Atlassian",
                category="development",
                used_seats=role.get("userCount", 0),
                total_seats=role.get("numberOfSeats"),
            )
            for role in self._get("/rest/api/3/applicationrole")
        ]
