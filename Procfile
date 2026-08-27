web: uvicorn main:app --host 0.0.0.0 --port $PORT
worker: celery -A backend.celery_app:celery_app worker -Q scheduling,inbound,fallback,escalation,reports --loglevel=info
beat: celery -A backend.celery_app:celery_app beat --loglevel=info