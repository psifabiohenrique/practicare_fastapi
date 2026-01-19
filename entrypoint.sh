#!/bin/sh
set -e

echo "Iniciando Celery worker..."
celery -A src.celery_app worker -l info --concurrency=1 &

echo "Iniciando FastAPI..."
exec  uvicorn src.main:app --host 0.0.0.0 --port 8080
