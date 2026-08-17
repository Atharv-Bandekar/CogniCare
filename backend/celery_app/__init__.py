"""
Initializes the Celery application instance.
"""
from celery import Celery
from backend.celery_app.config import CeleryConfig

celery_app = Celery("cognicare_worker")
celery_app.config_from_object(CeleryConfig)

# Auto-discover tasks in the tasks module
celery_app.autodiscover_tasks(['backend.celery_app'])