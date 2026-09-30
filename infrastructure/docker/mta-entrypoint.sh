#!/bin/sh
set -eu
export DJANGO_SETTINGS_MODULE=mta.mta_config.settings

attempt=1
max_attempts="${MTA_DB_STARTUP_ATTEMPTS:-30}"
delay_seconds="${MTA_DB_STARTUP_DELAY_SECONDS:-2}"

while ! python - <<'PY'
import django
django.setup()
from django.db import connection
with connection.cursor() as cursor:
    cursor.execute("SELECT 1")
    cursor.fetchone()
PY
do
    if [ "$attempt" -ge "$max_attempts" ]; then
        echo "MTA database readiness failed after ${attempt} attempts" >&2
        exit 1
    fi
    echo "MTA database unavailable; retry ${attempt}/${max_attempts}" >&2
    attempt=$((attempt + 1))
    sleep "$delay_seconds"
done

python manage.py migrate --noinput
python manage.py check

exec gunicorn mta.mta_config.wsgi:application \
    --bind "0.0.0.0:${MTA_PORT:-8000}" \
    --workers "${MTA_GUNICORN_WORKERS:-2}" \
    --access-logfile - \
    --error-logfile - \
    --capture-output
