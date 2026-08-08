"""
A small but real test suite. Run it with:  python manage.py test

These cover the three things most likely to break and hurt:
  1. Signup/auth actually issues working tokens.
  2. Tenant isolation - org A can never see org B's data.
  3. Alert rules fire exactly when they should, and respect cooldown.
"""
from django.contrib.auth import get_user_model
from django.core import mail
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.alerts.models import AlertEvent, AlertRule
from apps.alerts.services import evaluate_rules_for_organization
from apps.catalog.models import Application
from apps.licenses.models import LicensePool
from apps.tenants.models import Organization

User = get_user_model()

# A throwaway Fernet key so the encryption tests do not depend on your .env
TEST_KEY = "JgBhBqhc9tL51tg8HnMGdT-aOlWwRcz2VJix1UNrDdo="


def make_org(name: str, email: str):
    org = Organization.objects.create(name=name, primary_domain=email.split("@")[-1])
    user = User.objects.create_user(email=email, password="SuperSecret123!", organization=org)
    app = Application.objects.create(organization=org, name=f"{name} App", vendor="Vendor")
    pool = LicensePool.objects.create(
        organization=org, application=app, name="Standard",
        total_seats=100, used_seats=50, unit_cost=10,
    )
    return org, user, app, pool


def auth_client(user) -> APIClient:
    client = APIClient()
    response = client.post("/api/auth/login/",
                           {"email": user.email, "password": "SuperSecret123!"}, format="json")
    assert response.status_code == 200, response.data
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
    return client


class AuthTests(TestCase):
    def test_signup_creates_org_and_returns_tokens(self):
        client = APIClient()
        response = client.post("/api/auth/signup/", {
            "email": "founder@acme.com",
            "password": "VeryStrongPass99",
            "full_name": "Founder",
            "company_name": "Acme Corp",
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("access", response.data)
        user = User.objects.get(email="founder@acme.com")
        self.assertEqual(user.organization.name, "Acme Corp")
        self.assertEqual(user.organization.primary_domain, "acme.com")
        self.assertEqual(user.role, User.Role.OWNER)

    def test_signup_rejects_weak_password(self):
        response = APIClient().post("/api/auth/signup/", {
            "email": "weak@acme.com", "password": "password", "company_name": "Acme",
        }, format="json")
        self.assertEqual(response.status_code, 400)

    def test_me_requires_authentication(self):
        self.assertEqual(APIClient().get("/api/auth/me/").status_code, 401)


class TenantIsolationTests(TestCase):
    def setUp(self):
        self.org_a, self.user_a, self.app_a, self.pool_a = make_org("Acme", "a@acme.com")
        self.org_b, self.user_b, self.app_b, self.pool_b = make_org("Globex", "b@globex.com")

    def test_user_only_sees_own_applications(self):
        response = auth_client(self.user_a).get("/api/applications/")
        names = [row["name"] for row in response.data["results"]]
        self.assertEqual(names, ["Acme App"])

    def test_user_cannot_read_other_orgs_pool_by_id(self):
        response = auth_client(self.user_a).get(f"/api/license-pools/{self.pool_b.id}/")
        self.assertEqual(response.status_code, 404)

    def test_created_objects_are_stamped_with_callers_org(self):
        response = auth_client(self.user_a).post(
            "/api/applications/", {"name": "Notion", "vendor": "Notion Labs"}, format="json"
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Application.objects.get(name="Notion").organization, self.org_a)


class LicensePoolMathTests(TestCase):
    def setUp(self):
        self.org, self.user, self.app, self.pool = make_org("Acme", "a@acme.com")

    def test_derived_fields(self):
        self.assertEqual(self.pool.available_seats, 50)
        self.assertEqual(self.pool.utilization_pct, 50.0)
        self.assertFalse(self.pool.is_over_capacity)

    def test_over_capacity_and_zero_total(self):
        self.pool.used_seats = 120
        self.assertTrue(self.pool.is_over_capacity)
        self.pool.total_seats = 0
        self.assertEqual(self.pool.utilization_pct, 0.0)

    def test_dashboard_summary(self):
        response = auth_client(self.user).get("/api/dashboard/summary/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_seats"], 100)
        self.assertEqual(response.data["used_seats"], 50)
        self.assertEqual(response.data["available_seats"], 50)


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class AlertRuleTests(TestCase):
    def setUp(self):
        self.org, self.user, self.app, self.pool = make_org("Acme", "a@acme.com")
        mail.outbox = []

    def _rule(self, **kwargs):
        defaults = dict(
            organization=self.org, name="High utilisation",
            scope=AlertRule.Scope.ALL_POOLS,
            condition=AlertRule.Condition.UTILIZATION_ABOVE,
            threshold=90, recipients=["ops@acme.com"], cooldown_hours=24,
        )
        defaults.update(kwargs)
        return AlertRule.objects.create(**defaults)

    def test_does_not_fire_below_threshold(self):
        self._rule()
        self.assertEqual(evaluate_rules_for_organization(self.org), [])
        self.assertEqual(len(mail.outbox), 0)

    def test_fires_and_emails_above_threshold(self):
        self._rule()
        self.pool.used_seats = 95
        self.pool.save()
        events = evaluate_rules_for_organization(self.org)
        self.assertEqual(len(events), 1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("ops@acme.com", mail.outbox[0].to)
        self.assertTrue(events[0].email_sent)

    def test_cooldown_suppresses_duplicate(self):
        self._rule()
        self.pool.used_seats = 95
        self.pool.save()
        evaluate_rules_for_organization(self.org)
        evaluate_rules_for_organization(self.org)
        self.assertEqual(AlertEvent.objects.count(), 1)

    def test_available_seats_below_condition(self):
        self._rule(name="Low seats",
                   condition=AlertRule.Condition.AVAILABLE_SEATS_BELOW, threshold=5)
        self.pool.used_seats = 97
        self.pool.save()
        self.assertEqual(len(evaluate_rules_for_organization(self.org)), 1)

    def test_pool_scoped_rule_ignores_other_pools(self):
        other = LicensePool.objects.create(
            organization=self.org, application=self.app, name="Other",
            total_seats=10, used_seats=10,
        )
        self._rule(scope=AlertRule.Scope.POOL, license_pool=self.pool)
        self.assertEqual(evaluate_rules_for_organization(self.org), [])
        other.delete()

    def test_capacity_rules_stay_quiet_until_cap_is_entered(self):
        """
        Google cannot tell us purchased seats, so a freshly synced pool has
        total_seats = 0. Firing "0 seats available" for those would spam people.
        """
        self._rule(name="Low seats",
                   condition=AlertRule.Condition.AVAILABLE_SEATS_BELOW, threshold=5)
        self._rule(name="High util")
        self.pool.total_seats = 0
        self.pool.used_seats = 87
        self.pool.save()
        self.assertEqual(evaluate_rules_for_organization(self.org), [])

        # ...but once someone enters the cap, it fires normally.
        self.pool.total_seats = 88
        self.pool.save()
        self.assertEqual(len(evaluate_rules_for_organization(self.org)), 2)

    def test_rule_requires_recipients(self):
        client = auth_client(self.user)
        response = client.post("/api/alert-rules/", {
            "name": "No recipients", "scope": "all_pools",
            "condition": "utilization_above", "threshold": 80, "recipients": [],
        }, format="json")
        self.assertEqual(response.status_code, 400)


@override_settings(CREDENTIALS_ENCRYPTION_KEY=TEST_KEY, CONNECTORS_DEMO_MODE=True)
class ConnectorTests(TestCase):
    def setUp(self):
        self.org, self.user, _, _ = make_org("Acme", "a@acme.com")

    def test_provider_list_includes_expected_connectors(self):
        response = auth_client(self.user).get("/api/connectors/providers/")
        providers = {row["provider"] for row in response.data}
        self.assertTrue(
            {"google_workspace", "microsoft_365", "slack", "zoom", "atlassian", "manual"}
            <= providers
        )

    def test_credentials_round_trip_and_never_leak(self):
        client = auth_client(self.user)
        response = client.post("/api/connections/", {
            "provider": "google_workspace",
            "display_name": "GWS acme.com",
            "config": {"domain": "acme.com", "admin_email": "a@acme.com",
                       "customer_id": "my_customer"},
            "credentials": {"service_account_json": '{"type":"service_account"}'},
        }, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn("credentials", response.data)
        self.assertTrue(response.data["has_credentials"])

        from apps.connectors.models import Connection
        connection = Connection.objects.get(pk=response.data["id"])
        self.assertNotIn("service_account", connection.encrypted_credentials)
        self.assertEqual(
            connection.get_credentials()["service_account_json"],
            '{"type":"service_account"}',
        )

    def test_demo_sync_creates_pools(self):
        from apps.connectors.models import Connection
        from apps.connectors.services import sync_connection

        connection = Connection.objects.create(
            organization=self.org, provider="google_workspace",
            display_name="GWS", config={"domain": "acme.com", "admin_email": "a@acme.com"},
        )
        run = sync_connection(connection)
        self.assertEqual(run.status, "success", run.error_message)
        self.assertEqual(run.pools_created, 2)
        pool = LicensePool.objects.get(external_id="1010020028")
        self.assertEqual(pool.used_seats, 87)
        # Google cannot supply purchased seats, so it must stay at the manual value.
        self.assertEqual(pool.total_seats, 0)
        self.assertFalse(pool.total_seats_is_synced)

    def test_sync_does_not_clobber_manual_total_seats(self):
        from apps.connectors.models import Connection
        from apps.connectors.services import sync_connection

        connection = Connection.objects.create(
            organization=self.org, provider="google_workspace",
            display_name="GWS", config={"domain": "acme.com", "admin_email": "a@acme.com"},
        )
        sync_connection(connection)
        pool = LicensePool.objects.get(external_id="1010020028")
        pool.total_seats = 100
        pool.save()

        sync_connection(connection)
        pool.refresh_from_db()
        self.assertEqual(pool.total_seats, 100)
        self.assertEqual(pool.used_seats, 87)


class CSVImportTests(TestCase):
    def setUp(self):
        self.org, self.user, _, _ = make_org("Acme", "a@acme.com")

    def test_import_creates_applications_and_pools(self):
        import io

        from django.core.files.uploadedfile import SimpleUploadedFile

        csv_body = (
            "application,vendor,pool_name,sku,total_seats,used_seats,unit_cost,currency\n"
            "Notion,Notion Labs,Plus,notion-plus,50,31,10,USD\n"
            "Linear,Linear,Standard,linear-std,30,28,8,USD\n"
        )
        upload = SimpleUploadedFile("licenses.csv", csv_body.encode(), content_type="text/csv")
        response = auth_client(self.user).post(
            "/api/license-pools/import-csv/", {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["created"], 2)
        self.assertEqual(LicensePool.objects.get(name="Plus").used_seats, 31)

    def test_missing_column_is_rejected(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        upload = SimpleUploadedFile("bad.csv", b"foo,bar\n1,2\n", content_type="text/csv")
        response = auth_client(self.user).post(
            "/api/license-pools/import-csv/", {"file": upload}, format="multipart"
        )
        self.assertEqual(response.status_code, 400)
