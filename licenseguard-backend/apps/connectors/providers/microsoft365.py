"""
Microsoft 365 connector - Microsoft Graph `/subscribedSkus`.

Microsoft is the nice one: `prepaidUnits.enabled` is the number of seats you
PURCHASED and `consumedUnits` is how many are assigned. So unlike Google, this
connector can keep BOTH numbers up to date automatically.

SETUP (app-only / client credentials)
  1. Entra ID (Azure AD) -> App registrations -> New registration.
  2. Certificates & secrets -> New client secret. Copy the value.
  3. API permissions -> Microsoft Graph -> Application permissions ->
     `Organization.Read.All` and `User.Read.All` -> Grant admin consent.
  4. Copy Directory (tenant) ID and Application (client) ID.
"""
from __future__ import annotations

import requests
from django.conf import settings

from ..base import AssignmentData, BaseConnector, ConnectorError, PoolData
from ..registry import register

GRAPH = "https://graph.microsoft.com/v1.0"

SKU_NAMES = {
    "ENTERPRISEPACK": "Office 365 E3",
    "ENTERPRISEPREMIUM": "Office 365 E5",
    "SPB": "Microsoft 365 Business Premium",
    "O365_BUSINESS_ESSENTIALS": "Microsoft 365 Business Basic",
    "O365_BUSINESS_PREMIUM": "Microsoft 365 Business Standard",
    "POWER_BI_PRO": "Power BI Pro",
    "EMS": "Enterprise Mobility + Security E3",
}


@register
class Microsoft365Connector(BaseConnector):
    provider = "microsoft_365"
    label = "Microsoft 365"
    description = "Syncs purchased and consumed seats for every Microsoft 365 SKU via Graph."
    docs_url = "https://learn.microsoft.com/en-us/graph/api/subscribedsku-list"
    supports_total_seats = True
    config_fields = [
        {"key": "tenant_id", "label": "Directory (tenant) ID", "type": "text",
         "required": True, "secret": False},
        {"key": "client_id", "label": "Application (client) ID", "type": "text",
         "required": True, "secret": False},
        {"key": "client_secret", "label": "Client secret", "type": "password",
         "required": True, "secret": True},
    ]

    def _token(self) -> str:
        tenant = self.config.get("tenant_id")
        response = requests.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.config.get("client_id"),
                "client_secret": self.credentials.get("client_secret"),
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=30,
        )
        if response.status_code != 200:
            raise ConnectorError(f"Microsoft token request failed: {response.text[:300]}")
        return response.json()["access_token"]

    def _get(self, path: str) -> dict:
        response = requests.get(
            f"{GRAPH}{path}",
            headers={"Authorization": f"Bearer {self._token()}"},
            timeout=60,
        )
        if response.status_code != 200:
            raise ConnectorError(f"Graph call {path} failed: {response.text[:300]}")
        return response.json()

    def test_connection(self) -> dict:
        if settings.CONNECTORS_DEMO_MODE:
            return {"ok": True, "demo": True}
        data = self._get("/subscribedSkus")
        return {"ok": True, "message": f"Found {len(data.get('value', []))} SKUs."}

    def fetch_license_pools(self) -> list[PoolData]:
        if settings.CONNECTORS_DEMO_MODE:
            return [
                PoolData(external_id="ENTERPRISEPACK", name="Office 365 E3",
                         sku="ENTERPRISEPACK", application_name="Microsoft 365",
                         vendor="Microsoft", category="productivity",
                         used_seats=142, total_seats=150),
                PoolData(external_id="POWER_BI_PRO", name="Power BI Pro",
                         sku="POWER_BI_PRO", application_name="Microsoft 365",
                         vendor="Microsoft", category="productivity",
                         used_seats=18, total_seats=40),
            ]

        pools = []
        for sku in self._get("/subscribedSkus").get("value", []):
            part = sku.get("skuPartNumber", "")
            pools.append(PoolData(
                external_id=sku.get("skuId", part),
                name=SKU_NAMES.get(part, part),
                sku=part,
                application_name="Microsoft 365",
                vendor="Microsoft",
                category="productivity",
                used_seats=sku.get("consumedUnits", 0),
                total_seats=sku.get("prepaidUnits", {}).get("enabled", 0),
            ))
        return pools

    def fetch_assignments(self, pool: PoolData) -> list[AssignmentData]:
        if settings.CONNECTORS_DEMO_MODE:
            return []
        data = self._get("/users?$select=userPrincipalName,displayName,assignedLicenses&$top=999")
        return [
            AssignmentData(
                user_email=user.get("userPrincipalName", ""),
                user_name=user.get("displayName", ""),
            )
            for user in data.get("value", [])
            if any(lic.get("skuId") == pool.external_id
                   for lic in user.get("assignedLicenses", []))
        ]
