#!/bin/bash
# Start Celery Beat for scheduled periodic tasks

echo "Starting Celery Beat scheduler..."
celery -A app.tasks.celery_app beat --loglevel=info
