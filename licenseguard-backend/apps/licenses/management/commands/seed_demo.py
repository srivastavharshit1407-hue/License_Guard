"""
Populate a realistic demo organization so you can build the UI before you have
any real vendor credentials.

    python manage.py seed_demo --email you@example.com --password ChangeMe123!
"""
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.alerts.models import AlertRule
from apps.catalog.models import Application
from apps.connectors.models import Connection
from apps.licenses.models import LicensePool
from apps.tenants.models import Organization

# (application, vendor, category, [(pool name, total, used, unit cost, external_id)])
# The Google names/IDs match GoogleWorkspaceConnector's demo output on purpose,
# so running a demo sync updates these pools rather than duplicating them.
APPS = [
    ("Google Workspace", "Google", "productivity", [
        ("Google Workspace Business Standard", 100, 87, 12.00, "1010020028"),
        ("Google Workspace Enterprise Plus", 15, 12, 27.00, "1010020020"),
    ]),
    ("Slack", "Slack", "communication", [("Pro", 80, 63, 8.75, "slack-billable")]),
    ("Zoom", "Zoom", "communication", [("Zoom licensed hosts", 50, 44, 15.99, "zoom-licensed")]),
    ("Atlassian", "Atlassian", "development", [
        ("Jira Software", 100, 73, 7.75, "jira-software"),
        ("Confluence", 100, 61, 5.75, "confluence"),
    ]),
    ("Figma", "Figma", "design", [("Professional", 25, 9, 15.00, "")]),
    ("Adobe Creative Cloud", "Adobe", "design", [("All Apps", 12, 12, 59.99, "")]),
]


class Command(BaseCommand):
    help = "Create a demo organization with applications, licence pools and alert rules."

    def add_arguments(self, parser):
        parser.add_argument("--email", default="demo@licenseguard.local")
        parser.add_argument("--password", default="DemoPassw0rd!")
        parser.add_argument("--company", default="Acme Corp")

    def handle(self, *args, **options):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        email = options["email"].lower()
        domain = email.split("@")[-1]

        org, _ = Organization.objects.get_or_create(
            name=options["company"], defaults={"primary_domain": domain}
        )
        user, created = User.objects.get_or_create(
            email=email,
            defaults={"organization": org, "role": User.Role.OWNER, "full_name": "Demo Owner"},
        )
        if created:
            user.set_password(options["password"])
            user.save()

        for name, vendor, category, pools in APPS:
            application, _ = Application.objects.get_or_create(
                organization=org, name=name,
                defaults={"vendor": vendor, "category": category,
                          "owner_email": email, "description": f"{vendor} - {name}"},
            )
            for pool_name, total, used, cost, external_id in pools:
                LicensePool.objects.get_or_create(
                    organization=org, application=application, name=pool_name,
                    defaults={
                        "external_id": external_id,
                        "total_seats": total, "used_seats": used,
                        "unit_cost": cost, "currency": "USD",
                        "billing_cycle": "monthly",
                        "source": LicensePool.Source.MANUAL,
                        "last_synced_at": timezone.now(),
                    },
                )

        Connection.objects.get_or_create(
            organization=org, provider="google_workspace",
            display_name=f"Google Workspace - {domain}",
            defaults={"config": {"domain": domain, "customer_id": "my_customer",
                                 "admin_email": email}},
        )

        AlertRule.objects.get_or_create(
            organization=org, name="Any pool above 90% utilised",
            defaults={
                "scope": AlertRule.Scope.ALL_POOLS,
                "condition": AlertRule.Condition.UTILIZATION_ABOVE,
                "threshold": 90, "recipients": [email], "cooldown_hours": 24,
            },
        )
        AlertRule.objects.get_or_create(
            organization=org, name="Fewer than 5 seats left",
            defaults={
                "scope": AlertRule.Scope.ALL_POOLS,
                "condition": AlertRule.Condition.AVAILABLE_SEATS_BELOW,
                "threshold": 5, "recipients": [email], "cooldown_hours": 24,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            f"Demo ready.\n  Login: {email}\n  Password: {options['password']}"
        ))
