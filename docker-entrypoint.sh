#!/bin/sh
# Entrypoint del contenedor: espera la BD, aplica migraciones y arranca.

set -e

if [ "${DJANGO_DB_ENGINE:-sqlite}" = "postgres" ]; then
    echo "Waiting for PostgreSQL at ${POSTGRES_HOST:-db}:${POSTGRES_PORT:-5432}..."
    python - <<'PY'
import os, socket, time, sys
host = os.environ.get('POSTGRES_HOST', 'db')
port = int(os.environ.get('POSTGRES_PORT', '5432'))
deadline = time.time() + 30
while time.time() < deadline:
    try:
        with socket.create_connection((host, port), timeout=2):
            sys.exit(0)
    except OSError:
        time.sleep(1)
print(f'Database at {host}:{port} not reachable after 30s', file=sys.stderr)
sys.exit(1)
PY
fi

echo "Applying database migrations..."
python manage.py migrate --noinput

exec "$@"
