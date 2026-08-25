"""
Celery beat schedule for CogniCare's recurring work.

All times are interpreted in the worker's timezone (see CeleryConfig.timezone),
which is set to the product's primary market (Asia/Kolkata). Per-elder send times
are handled inside dispatch_daily_questions rather than with per-elder cron
entries, so this schedule stays small and static.
"""
from celery.schedules import crontab

BEAT_SCHEDULE = {
    # Every 15 minutes: queue daily questions for elders whose preferred time
    # just passed. Bounded to waking hours to avoid pointless overnight sweeps.
    "dispatch-daily-questions": {
        "task": "backend.celery_app.tasks.scheduling.dispatch_daily_questions",
        "schedule": crontab(minute="*/15", hour="5-22"),
        "options": {"queue": "scheduling"},
    },
    # Hourly: retire caregiver recommendations left pending for 12+ hours.
    "expire-stale-recommendations": {
        "task": "backend.celery_app.tasks.fallback.expire_stale_recommendations",
        "schedule": crontab(minute=0),
        "options": {"queue": "fallback"},
    },
    # Mondays 07:00: generate last week's report for every elder.
    "generate-weekly-reports": {
        "task": "backend.celery_app.tasks.reports.generate_all_weekly_reports",
        "schedule": crontab(hour=7, minute=0, day_of_week=1),
        "options": {"queue": "reports"},
    },
}
