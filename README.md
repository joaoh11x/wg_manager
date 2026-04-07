G Manager Backend

Flask-based backend (with a small built-in web UI) to manage WireGuard on MikroTik RouterOS.
It exposes HTTP endpoints for authentication and admin operations (interfaces, peers, rules, etc.)
and persists application state in a SQLAlchemy-backed database (Postgres by default).

## What this project does

- **Web UI** (server-rendered HTML + static assets) under `/ui/*`.
- **REST-like endpoints** for:
	- Authentication via JWT (`POST /login`).
	- Managing WireGuard interfaces and peers on MikroTik.
	- IP addresses, firewall rules, NAT rules, ACL, groups.
	- Basic system resource monitoring (including an SSE stream).
- **Persistence** using **Postgres + SQLAlchemy**.
- **Optional import/sync** of data from MikroTik into the database on container startup.

## Tech stack

- Python 3.11
- Flask + flask-cors
- Flask-JWT-Extended
- SQLAlchemy + Postgres (psycopg)
- RouterOS API client (`RouterOS-api`)

## Quick start (Docker Compose)

### Requirements

- Docker
- Docker Compose (v2)

### 1) (Optional) Create a `.env`

Docker Compose reads environment variables from your shell and/or a `.env` file.

Example:

```env
APP_ENV=development
FRONTEND_ORIGIN=http://localhost:3000

# Database (optional in Docker Compose: defaults are provided)
# DATABASE_URL=postgresql+psycopg://wireguard:wireguard@localhost:5432/wireguard_manager
# DB_SCHEMA=wireguard_manager

# If you set this, the container will use it.
ADMIN_PASSWORD=change-me

# For production, set a strong secret key.
SECRET_KEY=
JWT_SECRET_KEY=

# MikroTik connection (required for most admin operations)
MIKROTIK_HOST=
MIKROTIK_USER=
MIKROTIK_PASS=

# Optional: force plaintext login (defaults to true in dev, false in prod)
# MIKROTIK_PLAINTEXT_LOGIN=true

# Optional: one-time sync on startup
# RUN_MIKROTIK_SYNC_ON_START=1
```

### 2) Build and run

```bash
docker compose up --build
```

The app will be available at:

- UI: http://localhost:5000/ui/dashboard
- Login page: http://localhost:5000/login

### Database persistence (Docker)

Docker Compose starts a Postgres service and persists data in the named volume `pgdata`.
By default, the app uses `DATABASE_URL` pointing at the `postgres` service.

To reset the database:

```bash
docker compose down -v
```

## Run locally (Python)

### Requirements

- Python 3.11+

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure environment variables

You can export variables in your shell or create a `.env` file in the project root.
The app loads `.env` automatically via `python-dotenv`.

To run locally you need an accessible Postgres instance and:

- `DATABASE_URL` (e.g. `postgresql+psycopg://wireguard:wireguard@localhost:5432/wireguard_manager`)

To use MikroTik-backed features you also need:

- `MIKROTIK_HOST`
- `MIKROTIK_USER`
- `MIKROTIK_PASS`

### 3) Initialize the database

This ensures tables exist (idempotent) and creates/updates the `admin` user.

```bash
python init_db.py
```

Tip: you can run non-interactively by setting `ADMIN_PASSWORD`.

### 4) Start the server

```bash
export FLASK_DEBUG=1
python app/main.py
```

Open:

- http://127.0.0.1:5000/ui/dashboard

### Tip: run only Postgres via Docker

If you want to run Flask locally while using Postgres via Docker:

```bash
docker compose up -d postgres
export DATABASE_URL='postgresql+psycopg://wireguard:wireguard@localhost:5432/wireguard_manager'
python init_db.py
python app/main.py
```

## Environment variables

Common settings:

- `APP_ENV`: `development` (default) or `production`.
	- In production, the app requires `SECRET_KEY` or `JWT_SECRET_KEY`.
- `FLASK_HOST`: bind host (default `127.0.0.1`, Docker sets `0.0.0.0`).
- `FLASK_PORT`: bind port (default `5000`).
- `FLASK_DEBUG`: `1/true` to enable debug mode.
- `FRONTEND_ORIGIN`: allowed origin for CORS (default `http://localhost:3000`).

Security/auth:

- `SECRET_KEY`: Flask secret key.
- `JWT_SECRET_KEY`: JWT signing key (defaults to `SECRET_KEY`).
- `JWT_ACCESS_TOKEN_EXPIRES`: seconds (default `3600`).
- `ADMIN_PASSWORD`: password for the initial `admin` user (if not set, Docker init auto-generates one).

MikroTik integration:

- `MIKROTIK_HOST`, `MIKROTIK_USER`, `MIKROTIK_PASS`: required to connect to RouterOS API.
- `MIKROTIK_PLAINTEXT_LOGIN`: `true/false`.
	- If not set, defaults to **true in development** and **false in production**.
- `RUN_MIKROTIK_SYNC_ON_START`: `1/true` to run a one-time import when the Docker container starts.

Database:

- `DATABASE_URL`: database URL (Postgres). Also accepts `SQLALCHEMY_DATABASE_URI` / `DATABASE_URI`.
- `DB_SCHEMA` (optional): Postgres schema name to set in `search_path`.

Gunicorn (Docker):

- `GUNICORN_WORKERS`, `GUNICORN_THREADS`, `GUNICORN_TIMEOUT`, `GUNICORN_GRACEFUL_TIMEOUT`, `GUNICORN_KEEPALIVE`.

## API notes

- `POST /login` expects JSON: `{ "username": "admin", "password": "..." }` and returns a JWT.
- Protected endpoints require `Authorization: Bearer <access_token>`.

Example:

```bash
curl -s -X POST http://localhost:5000/login \
	-H 'Content-Type: application/json' \
	-d '{"username":"admin","password":"YOUR_PASSWORD"}'
```

### SSE (resource monitoring)

The `GET /system/resources/stream` endpoint is protected (JWT) and responds using Server-Sent Events.
Example (replace the token):

```bash
curl -N http://localhost:5000/system/resources/stream \
  -H 'Authorization: Bearer YOUR_TOKEN'
```

## Useful scripts

- Reset admin password (Postgres):

```bash
export DATABASE_URL='postgresql+psycopg://wireguard:wireguard@localhost:5432/wireguard_manager'
export NEW_ADMIN_PASSWORD='new-password'
python scripts/reset_admin_password.py
```

- Sync/import from MikroTik -> database (same logic used by the container when `RUN_MIKROTIK_SYNC_ON_START=1`):

```bash
export DATABASE_URL='postgresql+psycopg://wireguard:wireguard@localhost:5432/wireguard_manager'
export MIKROTIK_HOST='...'
export MIKROTIK_USER='...'
export MIKROTIK_PASS='...'
python scripts/sync_mikrotik_import.py --db-url "$DATABASE_URL"
```

- Migrate legacy SQLite -> Postgres:

```bash
export DATABASE_URL='postgresql+psycopg://wireguard:wireguard@localhost:5432/wireguard_manager'
python scripts/migrate_sqlite_to_postgres.py --sqlite-path database.db --postgres-url "$DATABASE_URL"
```

## Running tests

```bash
pytest
```

## Troubleshooting

- **"Missing MikroTik credentials"**: set `MIKROTIK_HOST`, `MIKROTIK_USER`, `MIKROTIK_PASS`.
- **Docker generated an admin password**: check container logs; it prints the generated `ADMIN_PASSWORD`.
- **Need a clean DB in Docker**: run `docker compose down -v` to remove the named volume.
- **"DATABASE_URL not configured"**: set `DATABASE_URL` (local) or use `docker compose up` (Docker injects a default value).
