"""
Weekly report tasks.

Beat triggers a fan-out that generates one report per elder for the 7-day cycle
that just ended. The heavy lifting (aggregation + LLM narrative) lives in
backend.reports.weekly_report — these tasks only handle scheduling and isolation.
"""
import logging
from datetime import date, timedelta

from backend.celery_app import celery_app
from backend.database.db import get_all_elders
from backend.reports.weekly_report import generate_weekly_report

logger = logging.getLogger(__name__)

CYCLE_LENGTH_DAYS = 7


def _last_cycle_bounds(today: date | None = None) -> tuple[date, date]:
    """
    Returns (cycle_start, cycle_end) for the 7-day cycle ending yesterday.

    WHY end yesterday: running early Monday should summarize the completed week,
    not a partial day that's still accruing interactions.
    """
    today = today or date.today()
    cycle_end = today - timedelta(days=1)
    cycle_start = cycle_end - timedelta(days=CYCLE_LENGTH_DAYS - 1)
    return cycle_start, cycle_end


@celery_app.task(name="backend.celery_app.tasks.reports.generate_all_weekly_reports")
def generate_all_weekly_reports():
    """
    Beat entry point: queues a weekly report for every elder.

    Returns:
        dict: {"elders": int, "queued": int, "cycle_start": str, "cycle_end": str}
    """
    cycle_start, cycle_end = _last_cycle_bounds()

    try:
        elders = get_all_elders() or []
    except Exception as exc:
        logger.error("Could not load elders for weekly reports: %s", exc)
        return {"elders": 0, "queued": 0, "cycle_start": str(cycle_start), "cycle_end": str(cycle_end)}

    queued = 0
    for elder in elders:
        try:
            generate_weekly_report_for_elder.apply_async(
                args=[elder["id"], cycle_start.isoformat(), cycle_end.isoformat()],
                queue="reports",
            )
            queued += 1
        except Exception as exc:
            logger.error("Failed to queue weekly report for %s: %s", elder.get("id"), exc)

    logger.info(
        "Weekly reports: queued %d/%d elders for %s..%s.", queued, len(elders), cycle_start, cycle_end
    )
    return {
        "elders": len(elders),
        "queued": queued,
        "cycle_start": cycle_start.isoformat(),
        "cycle_end": cycle_end.isoformat(),
    }


@celery_app.task(
    bind=True,
    name="backend.celery_app.tasks.reports.generate_weekly_report_for_elder",
    max_retries=2,
    default_retry_delay=600,
)
def generate_weekly_report_for_elder(self, elder_id: str, cycle_start: str, cycle_end: str):
    """
    Generates and stores one elder's weekly report.

    Args:
        elder_id (str): Elder profile UUID.
        cycle_start (str): ISO date, inclusive.
        cycle_end (str): ISO date, inclusive.

    Returns:
        dict: {"status": ..., "elder_id": ...}
    """
    try:
        generate_weekly_report(elder_id, cycle_start, cycle_end)
    except Exception as exc:
        logger.error("Weekly report failed for elder %s: %s", elder_id, exc)
        raise self.retry(exc=exc)

    logger.info("Weekly report generated for elder %s (%s..%s).", elder_id, cycle_start, cycle_end)
    return {"status": "generated", "elder_id": elder_id}
