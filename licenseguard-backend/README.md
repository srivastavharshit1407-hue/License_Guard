# LicenseGuard — Backend

Automated software licence inventory. Django 5 + Django REST Framework + Celery.

Pairs with [`licenseguard-frontend`](../licenseguard-frontend). This repo is the API and
all the logic; that repo is the UI.

---

## What this service does

| Concern | Where it lives |
|---|---|
| Tenants (multi-company isolation) | `apps/tenants` |
| Users, JWT login, Google SSO | `apps/accounts` |
| **Tab 1** — applications you hold licences for | `apps/catalog` |
| **Tab 2** — licence pools, caps, utilisation, seat holders | `apps/licenses` |
| **Tab 3** — threshold rules and alert emails | `apps/alerts` |
| Vendor integrations (the automatic part) | `apps/connectors` |

---

## Run it locally (5 minutes)

You need **Python 3.11+**. You do *not* need Postgres, Redis or Docker to start —
Django falls back to SQLite and the alert emails print to your terminal.

```bash
git clone https://github.com/<you>/licenseguard-backend.git
cd licenseguard-backend

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
```

Now open `.env` and fill in two values:

```bash
# 1. Any long random string
python -c "import secrets; print(secrets.token_urlsafe(50))"

# 2. The credential-encryption key (must be a valid Fernet key)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Then:

```bash
python manage.py migrate
python manage.py seed_demo --email you@example.com --password 'ChoosePassw0rd!'
python manage.py createsuperuser        # optional, for /admin/
python manage.py runserver
```

- API docs (interactive): <http://localhost:8000/api/docs/>
- Django admin: <http://localhost:8000/admin/>
- Health check: <http://localhost:8000/health/>

`seed_demo` creates a company with six applications, eight licence pools and two
alert rules, so the frontend has something to render on your first run.

Run the tests any time with `python manage.py test` (22 tests, all green).

---

## Demo mode

`.env` ships with `CONNECTORS_DEMO_MODE=True`. Every connector then returns
realistic fake data instead of calling the vendor. That means you can build and
demo the whole product — sync, dashboard, alerts — before you have a single API
credential.

Set it to `False` once you have real credentials.

---

## Connecting Google Workspace (the real thing)

This is the part you asked about most, so here it is precisely.

### The honest constraint, first

Google exposes **two** relevant APIs:

| API | Gives you |
|---|---|
| Enterprise License Manager (`licensing/v1`) | One record per **assigned** seat, grouped by SKU → your `used_seats` |
| Admin SDK Directory (`admin/directory_v1`) | Names, suspended status, `lastLoginTime` → powers "reclaim idle seats" |

There is **no general API that returns how many seats you purchased.** That number
lives in your contract or in the Reseller API (resellers only). So LicenseGuard:

- syncs `used_seats` automatically, and
- lets you type `total_seats` in once per SKU, and never overwrites it.

Microsoft 365, Zoom and Atlassian *do* expose the purchased count, and their
connectors sync both numbers. The "Syncs seat cap" badge on the Connections page
tells you which is which.

### Step by step

**1. Google Cloud Console** — <https://console.cloud.google.com>

- Create a project (e.g. `licenseguard`).
- **APIs & Services → Library** → enable:
  - `Admin SDK API`
  - `Enterprise License Manager API`

**2. Create a service account**

- **APIs & Services → Credentials → Create credentials → Service account**.
- Open it → **Keys → Add key → Create new key → JSON**. Download it.
- On the service account's **Details** tab, copy the **Unique ID** (a long number).

**3. Grant domain-wide delegation** — <https://admin.google.com>

- **Security → Access and data control → API controls → Domain-wide delegation**
- **Add new**, paste the Unique ID, and add these two scopes:

```
https://www.googleapis.com/auth/admin.directory.user.readonly
https://www.googleapis.com/auth/apps.licensing
```

**4. Connect it in LicenseGuard**

Go to the **Connections** tab → **Google Workspace → Connect**, and supply:

| Field | Value |
|---|---|
| Super-admin email | A real super-admin on your domain. Delegation acts *as* this user. |
| Customer ID | `my_customer` |
| Primary domain | `yourcompany.com` |
| Service account JSON | Paste the entire downloaded file |

Hit **Test**, then **Sync**. The JSON is encrypted with Fernet before it touches
the database and is never returned by the API.

> **Why a service account and not user OAuth?** Licence data is admin-scoped. A
> service account with domain-wide delegation gives you unattended background
> syncs with no refresh token to babysit and no dependency on one employee's
> account staying active.

---

## Google SSO (sign in with Google)

Separate from the connector above — this is just login.

1. **APIs & Services → Credentials → Create credentials → OAuth client ID → Web application.**
2. Authorised JavaScript origins: `http://localhost:5173` (and your production URL).
3. Copy the Client ID into **both**:
   - backend `.env` → `GOOGLE_OAUTH_CLIENT_ID`
   - frontend `.env` → `VITE_GOOGLE_CLIENT_ID`

Flow: the browser gets a signed ID token from Google → POSTs it to
`/api/auth/google/` → the backend verifies the signature against Google's public
keys and checks the audience → issues LicenseGuard JWTs. An unverified token is
never trusted; see `apps/accounts/google_sso.py`.

---

## Adding a new vendor

One file, two methods. Nothing else in the codebase changes.

```python
# apps/connectors/providers/notion.py
from ..base import BaseConnector, PoolData
from ..registry import register

@register
class NotionConnector(BaseConnector):
    provider = "notion"
    label = "Notion"
    description = "Syncs Notion workspace members."
    supports_total_seats = False
    config_fields = [
        {"key": "workspace_id", "label": "Workspace ID", "type": "text",
         "required": True, "secret": False},
        {"key": "api_token", "label": "Internal integration token",
         "type": "password", "required": True, "secret": True},
    ]

    def test_connection(self):
        ...
        return {"ok": True}

    def fetch_license_pools(self):
        return [PoolData(
            external_id="notion-members", name="Notion Plus",
            application_name="Notion", vendor="Notion",
            used_seats=count, total_seats=None,
        )]
```

Add `notion` to the import list in `apps/connectors/providers/__init__.py`. The
sync engine, the UI form, the dashboard and the alerts all pick it up
automatically — `config_fields` is what renders the connect dialog.

---

## Background jobs

Syncing on a schedule is what makes this "automatic" rather than a form. Start
Redis, then two more terminals:

```bash
docker compose up -d redis      # or install Redis natively
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

Default schedule (`config/celery.py`, editable from `/admin/` once beat is running):

| Task | Cadence |
|---|---|
| `sync_all_connections` | every 6 hours |
| `evaluate_all_alert_rules` | hourly at :15 |

Alerts are also re-evaluated immediately after every successful sync, so a
breach never waits for the next hourly tick.

---

## API reference

All routes require `Authorization: Bearer <access token>` except signup, login,
refresh and Google auth.

### Auth
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/signup/` | Create user **and** their organization |
| POST | `/api/auth/login/` | Email + password → JWT pair |
| POST | `/api/auth/refresh/` | Refresh token → new access token |
| POST | `/api/auth/google/` | Google ID token → JWT pair |
| GET | `/api/auth/me/` | Current user + org |

### Tab 1 — Applications
| Method | Path |
|---|---|
| GET / POST | `/api/applications/` |
| GET / PATCH / DELETE | `/api/applications/{id}/` |

### Tab 2 — Licences
| Method | Path | Purpose |
|---|---|---|
| GET / POST | `/api/license-pools/` | Pools with caps and utilisation |
| GET / PATCH / DELETE | `/api/license-pools/{id}/` | |
| GET | `/api/license-pools/{id}/assignments/` | Who holds the seats |
| POST | `/api/license-pools/import-csv/` | Bulk import (multipart) |
| GET | `/api/license-assignments/` | All seat holders, filterable |
| GET | `/api/dashboard/summary/` | Cards + at-risk pools |
| GET | `/api/sync-runs/` | Sync audit trail |

### Tab 3 — Alerts
| Method | Path | Purpose |
|---|---|---|
| GET / POST | `/api/alert-rules/` | Thresholds + recipients |
| GET / PATCH / DELETE | `/api/alert-rules/{id}/` | |
| POST | `/api/alert-rules/evaluate/` | Run every rule now |
| GET | `/api/alert-events/` | What has fired |
| POST | `/api/alert-events/{id}/acknowledge/` | |

### Connections
| Method | Path | Purpose |
|---|---|---|
| GET | `/api/connectors/providers/` | Available vendors + their required fields |
| GET / POST | `/api/connections/` | |
| POST | `/api/connections/{id}/test/` | Verify credentials |
| POST | `/api/connections/{id}/sync/` | Pull now |

CSV import columns: `application, vendor, pool_name, sku, total_seats,
used_seats, unit_cost, currency, renewal_date`
(`application`, `pool_name` and `total_seats` are required).

---

## Multi-tenancy

Every table inherits `OrgOwnedModel`, so every row carries an `organization` FK.
Every org-owned ViewSet mixes in `OrgScopedMixin`, which filters querysets to the
caller's org and stamps that org onto anything they create.

**If you write a new ViewSet, it must use `OrgScopedMixin`.** Without it a user
could read another company's licences by guessing an ID. `tests/test_api.py`
has three tests covering exactly this — keep them passing.

---

## Going to production

- [ ] `DJANGO_DEBUG=False`, real `DJANGO_SECRET_KEY`, real `DJANGO_ALLOWED_HOSTS`
- [ ] Postgres via `DATABASE_URL` (SQLite will not survive concurrent workers)
- [ ] `CREDENTIALS_ENCRYPTION_KEY` in a secrets manager, **not** in git.
      Rotating it means re-encrypting existing rows — decide before you have data.
- [ ] Real `EMAIL_BACKEND` (SMTP, SendGrid, SES, Resend…)
- [ ] `CORS_ALLOWED_ORIGINS` set to your frontend domain only
- [ ] HTTPS everywhere; add `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`
- [ ] Celery worker + beat running as managed processes
- [ ] Error tracking (Sentry) and DB backups

The included `Dockerfile` runs Gunicorn; `docker-compose.yml` is local Postgres
and Redis only.

---

## Layout

```
config/            settings, urls, celery
apps/
  tenants/         Organization, OrgOwnedModel, OrgScopedMixin
  accounts/        User, signup, JWT, Google SSO
  catalog/         Application            (Tab 1)
  licenses/        LicensePool, LicenseAssignment, SyncRun, CSV import  (Tab 2)
  connectors/      base, registry, crypto, sync engine, tasks
    providers/     google_workspace, microsoft365, slack, zoom, atlassian, manual
  alerts/          AlertRule, AlertEvent, evaluation, email  (Tab 3)
templates/alerts/  HTML + text alert emails
tests/             22 tests: auth, tenant isolation, alerts, connectors, CSV
```
