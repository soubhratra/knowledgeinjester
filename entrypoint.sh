#!/usr/bin/env bash
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput
exec uvicorn knowledgeinjester.asgi:application --host 0.0.0.0 --port 8000

