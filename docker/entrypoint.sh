#!/usr/bin/env sh
set -eu

# Persist the SQLite DB outside the image
mkdir -p /data

# Ensure the app always sees ./database.db in /app, but the file lives on the /data volume.
if [ ! -e "/app/database.db" ]; then
  ln -s /data/database.db /app/database.db
fi

# Initialize DB only if it doesn't exist yet (non-interactive).
if [ ! -f "/data/database.db" ]; then
  echo "[entrypoint] database.db not found; initializing..."
  python /app/docker_init_db.py
fi

# Optional: run MikroTik -> SQLite sync once on startup.
# Enable with RUN_MIKROTIK_SYNC_ON_START=1 (requires MIKROTIK_HOST/MIKROTIK_USER/MIKROTIK_PASS).
case "${RUN_MIKROTIK_SYNC_ON_START:-}" in
  1|true|TRUE|yes|YES|on|ON)
    if [ -z "${MIKROTIK_HOST:-}" ] || [ -z "${MIKROTIK_USER:-}" ] || [ -z "${MIKROTIK_PASS:-}" ]; then
      echo "[entrypoint] RUN_MIKROTIK_SYNC_ON_START enabled but MikroTik env vars are missing; skipping sync."
    else
      echo "[entrypoint] running sync_mikrotik_import.py..."
      python /app/sync_mikrotik_import.py --db-path /app/database.db
    fi
    ;;
esac

exec "$@"
