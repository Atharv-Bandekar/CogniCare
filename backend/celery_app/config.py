"""
Celery configuration for CogniCare.
Defines the strict queues needed to separate AI processing, scheduling, and escalation tasks.
"""
import os
from kombu import Queue

from backend.celery_app.beat_schedule import BEAT_SCHEDULE

class CeleryConfig:
    # Defaults to local Redis for development, overridden by env vars in production
    broker_url = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")
    result_backend = os.environ.get("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # Define the isolated queues requested in the architecture blueprint
    task_queues = (
        Queue('scheduling', routing_key='scheduling'),
        Queue('inbound', routing_key='inbound'),
        Queue('fallback', routing_key='fallback'),
        Queue('escalation', routing_key='escalation'),
        Queue('reports', routing_key='reports'),
    )

    task_default_queue = 'inbound'
    task_routes = {
        'backend.celery_app.tasks.inbound.*': {'queue': 'inbound'},
        'backend.celery_app.tasks.scheduling.*': {'queue': 'scheduling'},
        'backend.celery_app.tasks.fallback.*': {'queue': 'fallback'},
        'backend.celery_app.tasks.reports.*': {'queue': 'reports'},
    }

    # Recurring work (daily questions, 12h fallback sweep, weekly reports).
    beat_schedule = BEAT_SCHEDULE

    # WHY: crontab entries in beat_schedule are evaluated in this timezone.
    # Asia/Kolkata matches the product's primary market.
    timezone = os.environ.get("CELERY_TIMEZONE", "Asia/Kolkata")
    enable_utc = True

    # WHY: acks_late + reject_on_worker_lost means a task killed mid-flight is
    # redelivered rather than silently lost. The inbound pipeline is idempotent
    # on MessageSid, so redelivery is safe.
    task_acks_late = True
    task_reject_on_worker_lost = True

    # Keep a slow LLM/Twilio call from blocking a worker slot indefinitely.
    task_soft_time_limit = 120
    task_time_limit = 180