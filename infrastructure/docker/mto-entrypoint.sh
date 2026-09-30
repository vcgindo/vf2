#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py seed_all
python manage.py bootstrap_stage7b
python manage.py shell -c "from mto_app.models import DBRSettings; assert DBRSettings.objects.filter(flag='SystemType').exists(), 'MTO seed verification failed'"
python manage.py check --deploy
exec uvicorn MTO_API.asgi:application --host 0.0.0.0 --port 10015
