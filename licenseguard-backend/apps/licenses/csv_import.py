"""CSV import: the escape hatch for vendors without an API."""
from __future__ import annotations

import csv
import io
from datetime import datetime

from django.db import transaction

from apps.catalog.models import Application

from .models import LicensePool

REQUIRED_COLUMNS = {"application", "pool_name", "total_seats"}


def _to_int(value, default=0) -> int:
    try:
        return int(float(str(value).strip() or default))
    except (TypeError, ValueError):
        return default


def _to_date(value):
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


@transaction.atomic
def import_license_csv(organization, file_obj) -> dict:
    decoded = file_obj.read()
    if isinstance(decoded, bytes):
        decoded = decoded.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(decoded))

    headers = {(h or "").strip().lower() for h in (reader.fieldnames or [])}
    missing = REQUIRED_COLUMNS - headers
    if missing:
        raise ValueError(f"CSV is missing required column(s): {', '.join(sorted(missing))}")

    created = updated = 0
    errors: list[str] = []

    for line_no, row in enumerate(reader, start=2):
        row = {(k or "").strip().lower(): (v or "").strip() for k, v in row.items()}
        app_name = row.get("application")
        pool_name = row.get("pool_name")
        if not app_name or not pool_name:
            errors.append(f"Row {line_no}: application and pool_name are required.")
            continue

        application, _ = Application.objects.get_or_create(
            organization=organization,
            name=app_name,
            defaults={"vendor": row.get("vendor", "")},
        )
        pool, was_created = LicensePool.objects.update_or_create(
            organization=organization,
            application=application,
            name=pool_name,
            defaults={
                "sku": row.get("sku", ""),
                "source": LicensePool.Source.CSV,
                "total_seats": _to_int(row.get("total_seats")),
                "used_seats": _to_int(row.get("used_seats")),
                "unit_cost": row.get("unit_cost") or 0,
                "currency": (row.get("currency") or "USD").upper()[:3],
                "renewal_date": _to_date(row.get("renewal_date")),
            },
        )
        created += was_created
        updated += not was_created

    return {"created": created, "updated": updated, "errors": errors}
