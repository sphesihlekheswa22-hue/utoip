# Umzinyathi IT Operations Platform (UITOP)

Enterprise IT operations platform: Flask + Jinja2 UI with a versioned JWT REST API under `/api/v1`.

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
| Email | `admin@umzinyathi.gov.za` |
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
  -d "{\"email\":\"admin@umzinyathi.gov.za\",\"password\":\"Admin@UITOP2026\"}"

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

## Design

Light-first municipal teal theme (Plus Jakarta Sans), dark mode toggle, Chart.js dashboards, reusable KPI/table/form macros. Inventory modules use agent/discovery workflows (no manual Add forms).
