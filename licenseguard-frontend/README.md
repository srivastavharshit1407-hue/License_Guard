# LicenseGuard — Frontend

React 18 + Vite + Tailwind CSS. Talks to
[`licenseguard-backend`](../licenseguard-backend) over JSON.

---

## Screens

| Route | What it is |
|---|---|
| `/` | Landing page — product pitch, log in / sign up |
| `/signup` | Email + password, or Sign in with Google |
| `/login` | Same, for returning users |
| `/dashboard` | Cards, used-vs-unused chart, pools needing attention |
| `/applications` | **Tab 1** — every product you hold licences for |
| `/licenses` | **Tab 2** — caps, utilisation, cost of unused seats, CSV import |
| `/alerts` | **Tab 3** — threshold rules, recipients, alert history |
| `/connections` | Connect Google Workspace, M365, Slack, Zoom, Atlassian |

Everything after `/login` sits behind `<ProtectedRoute>`.

---

## Run it

Node 18+ required. **Start the backend first** — it must be on
`http://localhost:8000`.

```bash
git clone https://github.com/<you>/licenseguard-frontend.git
cd licenseguard-frontend

npm install
cp .env.example .env
npm run dev
```

Open <http://localhost:5173> and log in with the account you created via
`seed_demo` in the backend.

### `.env`

```bash
VITE_API_URL=http://localhost:8000
VITE_GOOGLE_CLIENT_ID=            # optional; enables the Google button
```

`VITE_GOOGLE_CLIENT_ID` must be the **same** OAuth client ID you put in the
backend's `GOOGLE_OAUTH_CLIENT_ID`, and `http://localhost:5173` must be listed
as an authorised JavaScript origin in Google Cloud Console. Leave it blank and
the Google button is replaced with a hint — email/password still works.

---

## How auth works here

`src/lib/api.js` owns one axios instance with two interceptors:

- **request** — attaches the access token from `localStorage`
- **response** — on a `401`, swaps the refresh token for a fresh access token and
  replays the original request exactly once. Parallel 401s collapse into a single
  refresh call. If the refresh fails, tokens are cleared and you land on `/login`.

So no page component ever thinks about tokens. `AuthContext` exposes
`user`, `login`, `signup`, `loginWithGoogle`, `logout`.

> `localStorage` is the pragmatic choice for a v1 and is what this scaffold uses.
> It is readable by any JavaScript on the page, so a XSS bug becomes a token
> leak. When you handle real customer data, move to httpOnly refresh cookies —
> it is a backend change plus swapping the storage calls here.

---

## Layout

```
src/
  lib/api.js              axios instance, token refresh, error formatting
  context/AuthContext.jsx auth state
  components/
    Layout.jsx            header + tab navigation
    ProtectedRoute.jsx    redirects anonymous users to /login
    GoogleSignInButton.jsx
    ui.jsx                StatCard, UsageBar, Badge, Alert, Modal, EmptyState, Spinner
  pages/                  Landing, Login, Signup, Dashboard, Applications,
                          Licenses, Alerts, Connections
```

The **Connections** page renders its form dynamically from
`GET /api/connectors/providers/`, using each provider's `config_fields`. Add a
connector in the backend and its setup dialog appears here with no frontend
change — including which fields are secret.

---

## Commands

```bash
npm run dev       # dev server on :5173
npm run build     # production bundle into dist/
npm run preview   # serve the built bundle locally
```

---

## Deploying

Vercel, Netlify or Cloudflare Pages all work with zero config:

- Build command: `npm run build`
- Output directory: `dist`
- Environment variables: `VITE_API_URL`, `VITE_GOOGLE_CLIENT_ID`

Then add your deployed URL to the backend's `CORS_ALLOWED_ORIGINS` and to the
Google OAuth client's authorised origins.

> Vite inlines `VITE_*` variables into the bundle at build time. They are public
> — never put a secret in one. The Google *client ID* is fine; a client *secret*
> is not.

Because this is a single-page app, configure your host to rewrite all paths to
`index.html`, otherwise refreshing on `/licenses` returns a 404.
