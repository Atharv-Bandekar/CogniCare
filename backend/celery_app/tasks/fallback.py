"""
Fallback task: retires caregiver recommendations that were never acted on.

A recommendation that sits 'pending' for 12+ hours has almost certainly been
missed, so we mark it 'timed_out' (a status the schema already allows). This keeps
the caregiver dashboard honest and stops stale suggestions accumulating.
"""
import logging

from backend.celery_app import celery_app
from backend.database.db import (
    get_pending_recommendations_older_than,
    update_recommendation_status,
)

logger = logging.getLogger(__name__)

# Blueprint's 12-hour window for caregiver action.
FALLBACK_TIMEOUT_HOURS = 12
TIMED_OUT_STATUS = "timed_out"


@celery_app.task(name="backend.celery_app.tasks.fallback.expire_stale_recommendations")
def expire_stale_recommendations(timeout_hours: int = FALLBACK_TIMEOUT_HOURS):
    """
    Marks pending recommendations older than `timeout_hours` as timed out.

    Args:
        timeout_hours (int): Age threshold in hours.

    Returns:
        dict: {"found": int, "expired": int}
    """
    try:
        stale = get_pending_recommendations_older_than(timeout_hours) or []
    except Exception as exc:
        logger.error("Could not query stale recommendations: %s", exc)
        return {"found": 0, "expired": 0}

    expired = 0
    for recommendation in stale:
        rec_id = (recommendation or {}).get("id")
        if not rec_id:
            continue
        try:
            update_recommendation_status(rec_id, TIMED_OUT_STATUS)
            expired += 1
        except Exception as exc:
            # WHY: one bad row (e.g. deleted mid-run) shouldn't stop the sweep.
            logger.error("Failed to expire recommendation %s: %s", rec_id, exc)

    if stale:
        logger.info("Fallback sweep: found %d stale recommendations, expired %d.", len(stale), expired)
    return {"found": len(stale), "expired": expired}
