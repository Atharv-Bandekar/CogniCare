"""
Initializes the Celery application instance.
"""
from celery import Celery
from backend.celery_app.config import CeleryConfig

celery_app = Celery("cognicare_worker")
celery_app.config_from_object(CeleryConfig)

# Register every task module so both the worker and beat can resolve task names.
# WHY imports rather than autodiscover_tasks: autodiscovery expects a `tasks`
# submodule per app package, which doesn't match this layout — explicit imports
# guarantee the beat schedule's task names are always registered.
celery_app.conf.imports = (
    "backend.celery_app.tasks.inbound",
    "backend.celery_app.tasks.scheduling",
    "backend.celery_app.tasks.fallback",
    "backend.celery_app.tasks.reports",
    "backend.celery_app.tasks.telegram_bot",
)