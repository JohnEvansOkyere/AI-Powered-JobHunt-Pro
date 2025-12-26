#!/bin/bash
# Start Celery Worker for processing background tasks

echo "Starting Celery worker..."
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
