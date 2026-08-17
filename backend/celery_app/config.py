"""
Celery configuration for CogniCare.
Defines the strict queues needed to separate AI processing, scheduling, and escalation tasks.
"""
import os
from kombu import Queue

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
    }