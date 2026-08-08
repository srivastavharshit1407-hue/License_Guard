# Building LicenseGuard — step by step

You are new to backend work, so this guide assumes nothing. Read it top to
bottom once, then work through Phase 0 → 6 in order.

Two repos are in this folder, already written and tested:

```
licenseguard-backend/    Django 5 + DRF + Celery — 22 tests passing
licenseguard-frontend/   React 18 + Vite + Tailwind — builds clean
```

---

## Part 1 — Django or FastAPI?

**Use Django (with Django REST Framework). It is the right call for this
project, and it is not close.**

Here is the reasoning rather than the verdict, because you will face this choice
again.

### What LicenseGuard actually needs

| Requirement | Django gives you | FastAPI needs you to assemble |
|---|---|---|
| Users, passwords, password hashing, reset flows | Built in | `passlib` + write it yourself |
| Database models and migrations | ORM + migrations, one command | SQLAlchemy + Alembic, configured by hand |
| Admin panel to eyeball and fix data | **Free.** `/admin/` with search and filters | No equivalent. Build a UI or use `psql` |
| Permissions and multi-tenant scoping | DRF permission classes | Write your own dependency layer |
| Background jobs on a schedule | `django-celery-beat`, editable from the admin | Celery works, but you wire the scheduler yourself |
| Google SSO, JWT, CORS, filtering, pagination | Mature packages that expect each other | Mature packages you integrate individually |

Roughly 70% of your first month would go on plumbing that Django ships with. The
admin panel alone is worth it: on day three you *will* need to look at a licence
pool and fix a wrong number, and with Django you already can.

### Where FastAPI genuinely wins

- **Async I/O throughput.** If you were fanning out thousands of concurrent
  vendor API calls, async would matter.
- **Automatic OpenAPI docs from type hints.** Excellent developer experience.
- **Lightweight microservices** where you want the framework out of the way.

### Why none of those decide it here

Your sync job runs **every six hours across a handful of vendors**. That is a
background job measured in seconds, not a latency-critical hot path — and it
runs in Celery, off the web process, so it does not block requests either way.
Optimising for async concurrency you will never use, at the cost of building
auth and an admin panel by hand, is the wrong trade.

On docs: this scaffold includes `drf-spectacular`, so you get interactive
OpenAPI docs at `/api/docs/` anyway.

### The honest caveat

Django is a bigger framework with more conventions to learn. `settings.py`,
apps, the ORM and the request/response cycle are real concepts you have to pick
up. FastAPI's surface area is smaller and you can hold all of it in your head
sooner. But "smaller framework" and "less work to ship this product" are not the
same thing, and for LicenseGuard they point in opposite directions.

**Verdict:** Django + DRF. Revisit only if you later add something like
real-time seat streaming or a very high-QPS public API — and even then, add a
small FastAPI service alongside rather than rewriting.

---

## Part 2 — Why two repos

You asked for separate repos, and that is a defensible choice. Be aware of the
trade:

**You gain:** independent deploys (Vercel for the UI, Railway/Fly for the API),
clean access control, separate CI, and a forced discipline that the API is the
only contract between them.

**You pay:** a change spanning both means two PRs, and you must keep them in
sync. Mitigate it by treating the OpenAPI schema at `/api/schema/` as the source
of truth, and by tagging matching releases (`v0.3.0` in both).

---

## Phase 0 — Set up the two GitHub repos

Install [Git](https://git-scm.com/downloads) and the
[GitHub CLI](https://cli.github.com/) first, then:

```bash
# --- Backend ---
cd licenseguard-backend
git init
git add .
git commit -m "Initial commit: Django API, connectors, alerts"
gh repo create licenseguard-backend --private --source=. --remote=origin --push

# --- Frontend ---
cd ../licenseguard-frontend
git init
git add .
git commit -m "Initial commit: React app, landing, dashboard, three tabs"
gh repo create licenseguard-frontend --private --source=. --remote=origin --push
```

No GitHub CLI? Create both repos in the web UI, then:

```bash
git remote add origin https://github.com/<you>/licenseguard-backend.git
git branch -M main
git push -u origin main
```

**Before your first push, confirm `.env` is ignored:**

```bash
git status --short | grep -i '\.env$'      # must print nothing
```

Both repos ship with a `.gitignore` that covers `.env`, `db.sqlite3`,
`node_modules/` and `.venv/`. A leaked `CREDENTIALS_ENCRYPTION_KEY` or Google
service-account JSON is the one mistake here that is genuinely expensive — and
GitHub history is forever, so deleting the file later does not undo it.

Working habit: branch per change, PR into `main`.

```bash
git checkout -b feat/slack-connector
# ...work...
git commit -am "Add Slack connector"
git push -u origin feat/slack-connector
gh pr create --fill
```

---

## Phase 1 — Get both running locally

**Backend** (details in `licenseguard-backend/README.md`):

```bash
cd licenseguard-backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Fill in the two generated values in `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(50))"                          # DJANGO_SECRET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"  # CREDENTIALS_ENCRYPTION_KEY
```

```bash
python manage.py migrate
python manage.py seed_demo --email you@example.com --password 'ChoosePassw0rd!'
python manage.py runserver
```

**Frontend**, in a second terminal:

```bash
cd licenseguard-frontend
npm install
cp .env.example .env
npm run dev
```

Open <http://localhost:5173>, log in, and click through all four tabs. Demo mode
is on, so everything works without a single vendor credential.

Then confirm the tests pass — `cd licenseguard-backend && python manage.py test`.
Get in the habit now; it is what will let you refactor confidently later.

**Do not move on until this works.** Everything after this builds on it.

---

## Phase 2 — Understand what you have

Spend an hour reading, in this order. The code is commented for exactly this.

1. `apps/tenants/models.py` — `Organization`, and why every table has an org FK
2. `apps/catalog/models.py` — `Application` (Tab 1)
3. `apps/licenses/models.py` — `LicensePool` (Tab 2). Read the docstring on why
   `total_seats` is manual by default; it is the central design constraint.
4. `apps/connectors/base.py` — the two-method contract every vendor implements
5. `apps/connectors/services.py` — the sync engine, vendor-agnostic
6. `apps/alerts/models.py` and `services.py` — thresholds, cooldown, email (Tab 3)

Then, to make it concrete: open `/admin/`, change a pool's `used_seats` to
something above its cap, and hit **Run checks now** on the Alerts tab. The alert
email prints in your backend terminal.

---

## Phase 3 — Connect Google Workspace for real

Full instructions with screenshots' worth of detail are in the backend README
under *Connecting Google Workspace*. The short version:

1. Google Cloud Console → new project → enable **Admin SDK API** and
   **Enterprise License Manager API**
2. Create a service account → download its JSON key → copy its **Unique ID**
3. Google Admin → Security → API controls → **Domain-wide delegation** → add
   that Unique ID with these scopes:
   `.../auth/admin.directory.user.readonly` and `.../auth/apps.licensing`
4. Set `CONNECTORS_DEMO_MODE=False` in `.env`, restart the server
5. Connections tab → Google Workspace → Connect → **Test** → **Sync**

**Read this before you are surprised by it:** Google has no API for how many
seats you *purchased*. LicenseGuard syncs `used_seats` automatically and lets you
type `total_seats` in once — sync never overwrites it. Microsoft 365, Zoom and
Atlassian *do* report the purchased count, and their connectors sync both.

---

## Phase 4 — Turn on the automation

Everything works without this, but syncing on a schedule is what makes
LicenseGuard a product instead of a form.

```bash
docker compose up -d redis
celery -A config worker -l info      # terminal 2
celery -A config beat   -l info \
  --scheduler django_celery_beat.schedulers:DatabaseScheduler   # terminal 3
```

Default cadence: sync every 6 hours, evaluate alerts hourly. Both are editable
from `/admin/` once beat has run once.

Switch alert email from console to real delivery in `.env`:

```bash
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...     # a Gmail App Password, not your account password
```

---

## Phase 5 — Make it yours

Ordered by value per hour of work:

1. **A second connector.** Microsoft 365 is already written — connect it and
   confirm it syncs both seat numbers. This proves the abstraction holds.
2. **Idle-seat reclamation.** `LicenseAssignment.last_active_at` is already
   synced from Google. Add a "seats unused for 90+ days" view — this is the
   feature that turns LicenseGuard from a report into money saved.
3. **Renewal reminders.** The `renewal_within_days` alert condition exists and
   works. Add a calendar view on top of it.
4. **Cost trends.** Snapshot `used_seats` per pool nightly and chart it. Without
   history you can only ever show today.
5. **Team invites.** The `User.role` field (owner/admin/viewer) exists but
   nothing enforces it yet. Add an invite flow and role-based permissions.
6. **Slack notifications** alongside email — a new delivery channel in
   `apps/alerts/services.py`.

---

## Phase 6 — Deploy

A setup that costs roughly $5–20/month to start:

| Piece | Where | Notes |
|---|---|---|
| Backend + worker + beat | Railway, Render or Fly.io | Three processes, one repo |
| Postgres | Same provider's managed DB | Set `DATABASE_URL` |
| Redis | Same provider's managed Redis | Set `CELERY_BROKER_URL` |
| Frontend | Vercel or Netlify | Build `npm run build`, output `dist` |
| Email | Resend, SendGrid or SES | Free tiers are ample at this volume |

Checklist before you point a real domain at it:

- [ ] `DJANGO_DEBUG=False`, real `DJANGO_SECRET_KEY`, real `DJANGO_ALLOWED_HOSTS`
- [ ] `CREDENTIALS_ENCRYPTION_KEY` in the host's secrets manager, not in git
- [ ] `CORS_ALLOWED_ORIGINS` = your frontend domain only
- [ ] HTTPS enforced; `SECURE_SSL_REDIRECT`, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`
- [ ] Automated database backups switched on
- [ ] Sentry (or similar) for errors
- [ ] Frontend `.env` points at the production API

---

## Things worth knowing before they bite you

**The `total_seats` problem is the product.** Most vendors tell you what is
*assigned*, not what is *paid for*. Any licence tool has to solve this with
manual entry, contract parsing, or reseller integrations. Deciding how you
handle it well is more of a differentiator than any amount of UI polish.

**Secrets are the main risk you are carrying.** You will hold service-account
keys and admin API tokens for other companies. They are Fernet-encrypted at rest
here, which is the right start — but if you sell this, expect security review
questions about key rotation, access logging and least-privilege scopes. Getting
scopes right (read-only, always) is cheap now and expensive to retrofit.

**Rate limits will find you.** Google, Slack and Atlassian all throttle. With a
handful of vendors you will not notice; at scale you need exponential backoff and
incremental sync. `SyncRun` already records every attempt, which is where you
will look when it starts happening.

**Tenant isolation is one line, and forgetting it is a breach.** Every org-owned
ViewSet must mix in `OrgScopedMixin`. Three tests in `tests/test_api.py` guard
this — do not delete them.

**Keep the tests green.** 22 exist. Add one whenever you add a connector or an
alert condition. That suite is what will let you change things in six months
without fear.

---

## Quick reference

```bash
# Backend
python manage.py runserver          # API on :8000
python manage.py test               # 22 tests
python manage.py migrate            # apply schema changes
python manage.py makemigrations     # after editing any models.py
python manage.py seed_demo          # realistic demo data
python manage.py createsuperuser    # for /admin/
celery -A config worker -l info     # background jobs

# Frontend
npm run dev                         # UI on :5173
npm run build                       # production bundle
```

| URL | What |
|---|---|
| <http://localhost:5173> | The app |
| <http://localhost:8000/api/docs/> | Interactive API docs |
| <http://localhost:8000/admin/> | Django admin |
