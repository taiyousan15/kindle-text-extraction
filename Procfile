# Procfile for Railway Multi-Service Deployment
# Each service will be deployed separately in Railway dashboard

# Main API service
web: uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2

# Celery worker for background tasks
worker: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=2

# Celery beat scheduler
beat: celery -A app.tasks.schedule beat --loglevel=info
