#!/bin/sh
set -eu

python manage.py migrate --noinput
python manage.py bootstrap_stage7b
python manage.py check --deploy
exec uvicorn apps.asgi:application --host 0.0.0.0 --port 10016
