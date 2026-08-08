"""
Google Workspace connector.

HOW THE INTEGRATION ACTUALLY WORKS
----------------------------------
Two Google APIs matter:

  1. Enterprise License Manager API (licensing/v1)
     `licenseAssignments.listForProduct` returns one record per ASSIGNED seat,
     grouped by SKU. Counting those records gives you `used_seats` per SKU.

  2. Admin SDK Directory API (admin/directory/v1)
     `users.list` gives you names, suspension state and lastLoginTime, which is
     what powers "this seat has been idle for 90 days, reclaim it".

WHAT GOOGLE WILL NOT TELL YOU
-----------------------------
There is no general API that returns how many seats you PURCHASED. That number
lives in your contract or in the Reseller API (only available to resellers). So:
  - `used_seats`  -> synced automatically, always accurate.
  - `total_seats` -> you type it in once per SKU; sync never overwrites it.
This is a real limitation of Google's platform, not a shortcut in this code.

AUTHENTICATION: SERVICE ACCOUNT + DOMAIN-WIDE DELEGATION
--------------------------------------------------------
  1. Google Cloud Console -> new project -> enable "Admin SDK API" and
     "Enterprise License Manager API".
  2. Create a service account, then create a JSON key for it and download it.
  3. On the service account, copy its "Unique ID" (a long number).
  4. Google Admin console -> Security -> Access and data control ->
     API controls -> Domain-wide delegation -> Add new. Paste the Unique ID and
     these scopes:
        https://www.googleapis.com/auth/admin.directory.user.readonly
        https://www.googleapis.com/auth/apps.licensing
  5. In LicenseGuard, create the connection with:
        admin_email        = a real super-admin address to impersonate
        customer_id        = "my_customer" (works for your own domain)
        domain             = acme.com
        service_account_json = paste the whole downloaded JSON
"""
from __future__ import annotations

import logging
from datetime import datetime

from django.conf import settings
from django.utils.dateparse import parse_datetime

from ..base import AssignmentData, BaseConnector, ConnectorError, PoolData
from ..registry import register

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/admin.directory.user.readonly",
    "https://www.googleapis.com/auth/apps.licensing",
]

# Product IDs worth scanning. Add more as you buy more Google products.
PRODUCT_IDS = [
    "Google-Apps",          # Google Workspace core SKUs
    "Google-Vault",         # Vault
    "Google-Drive-storage", # Extra Drive storage
    "101031",               # Google Workspace for Education
    "101033",               # Google Voice
]

# Friendly names for the SKUs people hit most often. Anything not listed falls
# back to the raw skuId, which is still perfectly usable.
# Full reference: https://developers.google.com/admin-sdk/licensing/v1/how-tos/products
SKU_NAMES = {
    "1010020027": "Google Workspace Business Starter",
    "1010020028": "Google Workspace Business Standard",
    "1010020025": "Google Workspace Business Plus",
    "1010060001": "Google Workspace Enterprise Essentials",
    "1010020020": "Google Workspace Enterprise Plus",
    "1010340002": "Google Workspace Enterprise Standard",
    "Google-Vault": "Google Vault",
    "Google-Vault-Former-Employee": "Google Vault (Former Employee)",
}


@register
class GoogleWorkspaceConnector(BaseConnector):
    provider = "google_workspace"
    label = "Google Workspace"
    description = (
        "Syncs assigned seats per Workspace SKU and each user's last sign-in. "
        "Purchased-seat counts must be entered manually - Google has no API for them."
    )
    docs_url = "https://developers.google.com/admin-sdk/licensing/v1/how-tos/products"
    supports_total_seats = False
    config_fields = [
        {"key": "admin_email", "label": "Super-admin email to impersonate",
         "type": "email", "required": True, "secret": False,
         "help": "Domain-wide delegation acts as this user."},
        {"key": "customer_id", "label": "Customer ID", "type": "text",
         "required": True, "secret": False, "default": "my_customer"},
        {"key": "domain", "label": "Primary domain", "type": "text",
         "required": True, "secret": False, "placeholder": "acme.com"},
        {"key": "service_account_json", "label": "Service account JSON key",
         "type": "textarea", "required": True, "secret": True,
         "help": "Paste the entire JSON file downloaded from Google Cloud."},
    ]

    # ------------------------------------------------------------------ auth
    def _build(self, api: str, version: str):
        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError as exc:  # pragma: no cover
            raise ConnectorError("google-api-python-client is not installed.") from exc

        raw = self.credentials.get("service_account_json")
        if not raw:
            raise ConnectorError("No service account JSON stored for this connection.")
        if isinstance(raw, str):
            import json
            try:
                raw = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ConnectorError("Service account JSON is not valid JSON.") from exc

        admin_email = self.config.get("admin_email")
        if not admin_email:
            raise ConnectorError("admin_email is required for domain-wide delegation.")

        creds = service_account.Credentials.from_service_account_info(
            raw, scopes=SCOPES
        ).with_subject(admin_email)
        return build(api, version, credentials=creds, cache_discovery=False)

    # ------------------------------------------------------------- contract
    def test_connection(self) -> dict:
        if settings.CONNECTORS_DEMO_MODE:
            return {"ok": True, "demo": True, "message": "Demo mode - no real call made."}
        try:
            service = self._build("admin", "directory_v1")
            result = service.users().list(
                customer=self.config.get("customer_id", "my_customer"), maxResults=1
            ).execute()
        except ConnectorError:
            raise
        except Exception as exc:
            raise ConnectorError(f"Google API call failed: {exc}") from exc
        return {"ok": True, "message": f"Reached Directory API ({len(result.get('users', []))} user sampled)."}

    def fetch_license_pools(self) -> list[PoolData]:
        if settings.CONNECTORS_DEMO_MODE:
            return self._demo_pools()

        service = self._build("licensing", "v1")
        customer = self.config.get("domain") or self.config.get("customer_id", "my_customer")
        counts: dict[str, dict] = {}

        for product_id in PRODUCT_IDS:
            page_token = None
            while True:
                try:
                    response = service.licenseAssignments().listForProduct(
                        productId=product_id,
                        customerId=customer,
                        maxResults=1000,
                        pageToken=page_token,
                    ).execute()
                except Exception as exc:
                    # A product you do not own returns 404 - that is expected, skip it.
                    logger.info("Skipping product %s: %s", product_id, exc)
                    break

                for item in response.get("items", []):
                    sku_id = item.get("skuId", "unknown")
                    bucket = counts.setdefault(sku_id, {
                        "count": 0,
                        "sku_name": item.get("skuName") or SKU_NAMES.get(sku_id, sku_id),
                        "product_name": item.get("productName") or "Google Workspace",
                        "users": [],
                    })
                    bucket["count"] += 1
                    bucket["users"].append(item.get("userId", ""))

                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        return [
            PoolData(
                external_id=sku_id,
                name=data["sku_name"],
                sku=sku_id,
                application_name="Google Workspace",
                vendor="Google",
                category="productivity",
                used_seats=data["count"],
                total_seats=None,  # Google will not tell us; keep whatever the user typed.
                metadata={"user_emails": data["users"]},
            )
            for sku_id, data in counts.items()
        ]

    def fetch_assignments(self, pool: PoolData) -> list[AssignmentData]:
        emails = pool.metadata.get("user_emails", [])
        if settings.CONNECTORS_DEMO_MODE:
            return [AssignmentData(user_email=e, user_name=e.split("@")[0].title()) for e in emails]
        if not emails:
            return []

        directory = self._build("admin", "directory_v1")
        profiles: dict[str, dict] = {}
        page_token = None
        while True:
            response = directory.users().list(
                customer=self.config.get("customer_id", "my_customer"),
                maxResults=500,
                projection="full",
                pageToken=page_token,
            ).execute()
            for user in response.get("users", []):
                profiles[user.get("primaryEmail", "").lower()] = user
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        assignments = []
        for email in emails:
            profile = profiles.get(email.lower(), {})
            last_login = profile.get("lastLoginTime")
            assignments.append(AssignmentData(
                user_email=email,
                user_name=profile.get("name", {}).get("fullName", ""),
                external_id=profile.get("id", ""),
                status="suspended" if profile.get("suspended") else "active",
                assigned_at=_parse(profile.get("creationTime")),
                last_active_at=_parse(last_login),
            ))
        return assignments

    # ------------------------------------------------------------ demo data
    def _demo_pools(self) -> list[PoolData]:
        domain = self.config.get("domain", "example.com")
        standard_users = [f"user{i:02d}@{domain}" for i in range(1, 88)]
        plus_users = [f"exec{i:02d}@{domain}" for i in range(1, 13)]
        return [
            PoolData(
                external_id="1010020028", name="Google Workspace Business Standard",
                sku="1010020028", application_name="Google Workspace", vendor="Google",
                category="productivity", used_seats=len(standard_users), total_seats=None,
                metadata={"user_emails": standard_users},
            ),
            PoolData(
                external_id="1010020020", name="Google Workspace Enterprise Plus",
                sku="1010020020", application_name="Google Workspace", vendor="Google",
                category="productivity", used_seats=len(plus_users), total_seats=None,
                metadata={"user_emails": plus_users},
            ),
        ]


def _parse(value: str | None) -> datetime | None:
    return parse_datetime(value) if value else None
