"""
Zoom connector - Server-to-Server OAuth.

`GET /v2/accounts/me/plans` returns your plan's purchased host count, and
`GET /v2/users?status=active` lists users you can filter to licensed (type 2).
So Zoom can supply both numbers.

SETUP
  1. marketplace.zoom.us -> Develop -> Build App -> Server-to-Server OAuth.
  2. Scopes: `user:read:admin`, `account:read:admin`, `billing:read:admin`.
  3. Copy Account ID, Client ID, Client Secret.
"""
from __future__ import annotations

import base64

import requests
from django.conf import settings

from ..base import AssignmentData, BaseConnector, ConnectorError, PoolData
from ..registry import register

API = "https://api.zoom.us/v2"


@register
class ZoomConnector(BaseConnector):
    provider = "zoom"
    label = "Zoom"
    description = "Syncs licensed Zoom hosts against your purchased host count."
    docs_url = "https://developers.zoom.us/docs/internal-apps/s2s-oauth/"
    supports_total_seats = True
    config_fields = [
        {"key": "account_id", "label": "Account ID", "type": "text",
         "required": True, "secret": False},
        {"key": "client_id", "label": "Client ID", "type": "text",
         "required": True, "secret": False},
        {"key": "client_secret", "label": "Client secret", "type": "password",
         "required": True, "secret": True},
    ]

    def _token(self) -> str:
        basic = base64.b64encode(
            f"{self.config.get('client_id')}:{self.credentials.get('client_secret')}".encode()
        ).decode()
        response = requests.post(
            "https://zoom.us/oauth/token",
            headers={"Authorization": f"Basic {basic}"},
            params={"grant_type": "account_credentials",
                    "account_id": self.config.get("account_id")},
            timeout=30,
        )
        if response.status_code != 200:
            raise ConnectorError(f"Zoom token request failed: {response.text[:300]}")
        return response.json()["access_token"]

    def _get(self, path: str, params: dict | None = None) -> dict:
        response = requests.get(
            f"{API}{path}",
            headers={"Authorization": f"Bearer {self._token()}"},
            params=params or {},
            timeout=60,
        )
        if response.status_code != 200:
            raise ConnectorError(f"Zoom call {path} failed: {response.text[:300]}")
        return response.json()

    def test_connection(self) -> dict:
        if settings.CONNECTORS_DEMO_MODE:
            return {"ok": True, "demo": True}
        self._get("/users", {"page_size": 1})
        return {"ok": True, "message": "Zoom API reachable."}

    def fetch_license_pools(self) -> list[PoolData]:
        if settings.CONNECTORS_DEMO_MODE:
            users = [f"host{i:02d}@example.com" for i in range(1, 45)]
            return [PoolData(
                external_id="zoom-licensed", name="Zoom Pro (licensed hosts)",
                application_name="Zoom", vendor="Zoom", category="communication",
                used_seats=len(users), total_seats=50,
                metadata={"user_emails": users},
            )]

        try:
            plans = self._get("/accounts/me/plans")
            total = plans.get("plan_base", {}).get("hosts")
        except ConnectorError:
            total = None  # billing scope may not be granted; fall back to manual

        emails, page_token = [], None
        while True:
            page = self._get("/users", {
                "status": "active", "page_size": 300,
                **({"next_page_token": page_token} if page_token else {}),
            })
            for user in page.get("users", []):
                if user.get("type") in (2, 3):  # 2 = Licensed, 3 = On-prem
                    emails.append(user.get("email", ""))
            page_token = page.get("next_page_token")
            if not page_token:
                break

        return [PoolData(
            external_id="zoom-licensed", name="Zoom licensed hosts",
            application_name="Zoom", vendor="Zoom", category="communication",
            used_seats=len(emails), total_seats=total,
            metadata={"user_emails": emails},
        )]

    def fetch_assignments(self, pool: PoolData) -> list[AssignmentData]:
        return [AssignmentData(user_email=e) for e in pool.metadata.get("user_emails", []) if e]
