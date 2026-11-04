# UITOP — Unified IT Operations Platform

Enterprise IT operations platform: Flask + Jinja2 UI with a versioned JWT REST API under `/api/v1`.

## Organization branding

Set your company name and email domain via **Settings → General** in the admin UI, or environment variables before first seed:

- `ORG_NAME` — display name (e.g. Acme Corporation)
- `ORG_EMAIL_DOMAIN` — default email domain for demo accounts (e.g. `acme.com`)
- `UITOP_ADMIN_EMAIL` — optional override for the seeded super-admin login

## Quick start

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env          # optional

set FLASK_APP=app:app           # PowerShell: $env:FLASK_APP="app:app"
flask db upgrade
flask seed
python app.py
```

Open http://127.0.0.1:5500/login

### Default admin (after `flask seed`)

| Field | Value |
|-------|-------|
| Email | `admin@example.com` |
| Password | `Admin@UITOP2026` |

Change this password before any non-local deployment.

## API overview

Base URL: `/api/v1`

Success envelope: `{ "data": ..., "meta": ... }`  
Error envelope: `{ "error": { "code", "message", "details" } }`

### Auth

```bash
# Login
curl -s -X POST http://127.0.0.1:5500/api/v1/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@example.com\",\"password\":\"Admin@UITOP2026\"}"

# Current user
curl -s http://127.0.0.1:5500/api/v1/auth/me -H "Authorization: Bearer <access_token>"

# Refresh
curl -s -X POST http://127.0.0.1:5500/api/v1/auth/refresh ^
  -H "Content-Type: application/json" ^
  -d "{\"refresh_token\":\"<refresh_token>\"}"
```

Other areas: `/users`, `/roles`, `/departments`, `/audit`, `/agents/*`, `/computers`, `/servers`, `/network/devices`, `/printers`.

### Agents (Windows agent protocol)

1. Admin creates enrollment token: `POST /api/v1/agents/enrollment-tokens` (JWT + `agents:manage`)
2. Agent registers: `POST /api/v1/agents/register` with `enrollment_token` → receives `client_id` / `client_secret` / `agent_id` (secret shown once)
3. Agent exchanges credentials: `POST /api/v1/agents/token` → **agent JWT** (`token_use=agent`, 1h)
4. Authenticated telemetry (Bearer agent JWT + scopes):

| Endpoint | Scope | Purpose |
|----------|-------|---------|
| `POST /agents/heartbeat` | `agents:heartbeat` | Update `last_seen`, `status`, `agent_version` |
| `POST /agents/inventory` | `agents:inventory` | Upsert linked `Computer` inventory |
| `POST /agents/performance` | `agents:performance` | Store `PerformanceSample` rows |
| `POST /agents/events` | `agents:events` | Store `AgentEvent` rows |
| `POST /agents/alerts` | `agents:alerts` | Store `AgentAlert` rows |

All agent actions are written to `AuditLog`. Client secrets are stored hashed and never returned after registration.

### Site connector (LAN discovery for cloud deploy)

When UITOP runs on Render/Neon, the cloud host cannot scan your office LAN. Run **one** always-on PC on-prem:

1. In UITOP: **Network → Site Connector** → generate enrollment token
2. On the LAN PC (Python 3):

```powershell
irm https://YOUR-APP.onrender.com/network/site-connector/install.ps1 | iex
Install-UitopSiteConnector -Token 'enroll_…' -Server 'https://YOUR-APP.onrender.com' -Site 'HQ'
```

3. Connector heartbeats and POSTs scan results to `/api/v1/connectors/*`
4. Each managed PC still needs the normal UITOP Agent for rich inventory / My Devices



## CLI

```bash
flask db migrate -m "message"
flask db upgrade
flask seed
flask create-admin --email admin@example.com --password 'Secret123!'
```

## Configuration

Environment variables (see `.env.example`):

- `SECRET_KEY`, `JWT_SECRET_KEY`
- `DATABASE_URL` — defaults to SQLite `instance/uitop.db`; set Postgres URL for production
- `CORS_ORIGINS` — comma-separated or `*`
- `FLASK_ENV` — `development` | `testing` | `production`

## Structure

```
uitop/           Application package (factory, models, services, /api/v1)
migrations/      Alembic migrations
routes/          Existing Jinja UI blueprints
templates/       Jinja layouts and modules
static/          CSS / JS design system
app.py           Dev entrypoint
wsgi.py          Production WSGI (gunicorn)
```

## Production note

```bash
gunicorn -w 4 -b 0.0.0.0:5500 wsgi:app
```

**Render:** see [DEPLOY_RENDER.md](DEPLOY_RENDER.md) and `render.yaml` (GitHub: [utoip](https://github.com/sphesihlekheswa22-hue/utoip)).

## Design

Light-first organizational teal theme (Plus Jakarta Sans), dark mode toggle, Chart.js dashboards, reusable KPI/table/form macros. Inventory modules use agent/discovery workflows (no manual Add forms).
