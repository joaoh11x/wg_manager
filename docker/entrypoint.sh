#!/usr/bin/env sh
set -eu

# Wait for the database to become available (best-effort).
DB_URL="${DATABASE_URL:-${SQLALCHEMY_DATABASE_URI:-${DATABASE_URI:-}}}"
if [ -n "${DB_URL}" ]; then
  echo "[entrypoint] waiting for database..."
  python - <<'PY'
import os
import time
from sqlalchemy import create_engine, text

url = os.environ.get("DATABASE_URL") or os.environ.get("SQLALCHEMY_DATABASE_URI") or os.environ.get("DATABASE_URI")
engine = create_engine(url, pool_pre_ping=True)
deadline = time.time() + 60
last_err = None

while time.time() < deadline:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        last_err = None
        break
    except Exception as e:
        last_err = e
        time.sleep(2)

if last_err:
    raise SystemExit(f"Database not ready after 60s: {last_err}")
print("[entrypoint] database is ready")
PY
fi

# Ensure schema + admin exist (idempotent).
echo "[entrypoint] ensuring database schema..."
python /app/docker_init_db.py

# Optional: run MikroTik -> SQLite sync once on startup.
# Enable with RUN_MIKROTIK_SYNC_ON_START=1 (requires MIKROTIK_HOST/MIKROTIK_USER/MIKROTIK_PASS).
case "${RUN_MIKROTIK_SYNC_ON_START:-}" in
  1|true|TRUE|yes|YES|on|ON)
    if [ -z "${MIKROTIK_HOST:-}" ] || [ -z "${MIKROTIK_USER:-}" ] || [ -z "${MIKROTIK_PASS:-}" ]; then
      echo "[entrypoint] RUN_MIKROTIK_SYNC_ON_START enabled but MikroTik env vars are missing; skipping sync."
    else
      echo "[entrypoint] running sync_mikrotik_import.py..."
      python /app/scripts/sync_mikrotik_import.py --db-url "${DB_URL}"
    fi
    ;;
esac

exec "$@"
