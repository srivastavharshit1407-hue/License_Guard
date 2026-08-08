"""
Slack connector.

`team.billableInfo` returns, per user, whether Slack will bill you for them this
month - which is exactly the number that drives your invoice. Purchased seats
are not exposed by the API on most plans, so enter that manually.

SETUP
  1. api.slack.com/apps -> Create New App -> From scratch.
  2. OAuth & Permissions -> User Token Scopes: `users:read`, `users:read.email`,
     `admin` (needed for team.billableInfo).
  3. Install to workspace, copy the User OAuth Token (starts with xoxp-).
"""
from __future__ import annotations

import requests
from django.conf import settings

from ..base import AssignmentData, BaseConnector, ConnectorError, PoolData
from ..registry import register


@register
class SlackConnector(BaseConnector):
    provider = "slack"
    label = "Slack"
    description = "Counts billable Slack members. Purchased seats are entered manually."
    docs_url = "https://api.slack.com/methods/team.billableInfo"
    supports_total_seats = False
    config_fields = [
        {"key": "workspace_name", "label": "Workspace name", "type": "text",
         "required": False, "secret": False},
        {"key": "access_token", "label": "User OAuth token (xoxp-...)",
         "type": "password", "required": True, "secret": True},
    ]

    def _call(self, method: str, params: dict | None = None) -> dict:
        response = requests.get(
            f"https://slack.com/api/{method}",
            headers={"Authorization": f"Bearer {self.credentials.get('access_token')}"},
            params=params or {},
            timeout=30,
        )
        data = response.json()
        if not data.get("ok"):
            raise ConnectorError(f"Slack {method} failed: {data.get('error')}")
        return data

    def test_connection(self) -> dict:
        if settings.CONNECTORS_DEMO_MODE:
            return {"ok": True, "demo": True}
        info = self._call("auth.test")
        return {"ok": True, "message": f"Connected to {info.get('team')}."}

    def fetch_license_pools(self) -> list[PoolData]:
        if settings.CONNECTORS_DEMO_MODE:
            members = [f"member{i:02d}@example.com" for i in range(1, 64)]
            return [PoolData(
                external_id="slack-billable", name="Slack Pro (billable members)",
                application_name="Slack", vendor="Slack", category="communication",
                used_seats=len(members), total_seats=None,
                metadata={"user_emails": members},
            )]

        billable = self._call("team.billableInfo").get("billable_info", {})
        billable_ids = {uid for uid, info in billable.items() if info.get("billing_active")}

        emails, cursor = [], None
        while True:
            page = self._call("users.list", {"limit": 200, "cursor": cursor})
            for member in page.get("members", []):
                if member.get("id") in billable_ids and not member.get("is_bot"):
                    emails.append(member.get("profile", {}).get("email", "") or member.get("name"))
            cursor = page.get("response_metadata", {}).get("next_cursor")
            if not cursor:
                break

        return [PoolData(
            external_id="slack-billable",
            name=f"Slack ({self.config.get('workspace_name', 'workspace')}) billable members",
            application_name="Slack", vendor="Slack", category="communication",
            used_seats=len(billable_ids), total_seats=None,
            metadata={"user_emails": emails},
        )]

    def fetch_assignments(self, pool: PoolData) -> list[AssignmentData]:
        return [AssignmentData(user_email=e) for e in pool.metadata.get("user_emails", []) if e]
