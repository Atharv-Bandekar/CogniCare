"""
Weekly report orchestrator (Phase 3A).

Public contract:
    generate_weekly_report(elder_id: str, cycle_start, cycle_end) -> dict

Responsibilities:
- Pull the cycle's interactions + insights + family activity from the DB layer.
- Delegate the narrative (engagement/emotional trend, recurring topics) to the
  existing, tested `generate_weekly_summary` LLM summarizer.
- Aggregate structured fields (domains completed, family engagement).
- Persist a record matching the `weekly_reports` table and return it.

HARD RULE (non-clinical) is enforced inside `generate_weekly_summary`'s system
prompt; this orchestrator only shapes and stores data.
"""
import logging
from typing import Any, Dict, List

from backend.database.db import (
    get_elder_profile,
    get_interactions_by_elder,
    get_insights_by_elder,
    get_recommendations_by_elder,
    insert_weekly_report,
)
from backend.agents.report_generator import generate_weekly_summary

logger = logging.getLogger(__name__)

# Recommendation status that means the caregiver has not yet acted.
_PENDING_STATUS = "pending"


def _iso_date(value) -> str:
    """Normalizes a date/datetime/string to a 'YYYY-MM-DD' string."""
    if hasattr(value, "isoformat"):
        return value.isoformat()[:10]
    return str(value)[:10]


def _in_window(date_value, start, end) -> bool:
    """Inclusive [start, end] comparison on the date portion only."""
    if not date_value:
        return False
    d = _iso_date(date_value)
    return _iso_date(start) <= d <= _iso_date(end)


def _summarize_family_engagement(elder_id: str, cycle_start, cycle_end) -> Dict[str, int]:
    """Counts recommendations sent vs acted-on during the cycle."""
    try:
        recs: List[Dict[str, Any]] = get_recommendations_by_elder(elder_id) or []
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Could not fetch recommendations for family engagement: %s", exc)
        return {"recommendations_sent": 0, "recommendations_acted_on": 0}

    in_cycle = [r for r in recs if _in_window(r.get("created_at"), cycle_start, cycle_end)]
    acted = [r for r in in_cycle if (r.get("status") or _PENDING_STATUS) != _PENDING_STATUS]
    return {
        "recommendations_sent": len(in_cycle),
        "recommendations_acted_on": len(acted),
    }


def generate_weekly_report(elder_id: str, cycle_start, cycle_end) -> Dict[str, Any]:
    """
    Build and persist the weekly report for one elder over [cycle_start, cycle_end].

    Args:
        elder_id (str): Elder profile UUID.
        cycle_start: Cycle start date (date or 'YYYY-MM-DD' string), inclusive.
        cycle_end: Cycle end date (date or 'YYYY-MM-DD' string), inclusive.

    Returns:
        dict: The persisted weekly_reports record (or the assembled record if the
              DB returns nothing).
    """
    profile = get_elder_profile(elder_id) or {}
    insights = get_insights_by_elder(elder_id, cycle_start, cycle_end) or []

    # get_interactions_by_elder returns newest-first; filter to the cycle window
    # and re-sort oldest-first so it aligns with insights for the summary prompt.
    all_interactions = get_interactions_by_elder(elder_id, limit=50) or []
    window_interactions = [
        i for i in all_interactions if _in_window(i.get("interaction_date"), cycle_start, cycle_end)
    ]
    window_interactions.sort(key=lambda i: _iso_date(i.get("interaction_date")))

    domains_completed = sorted({i.get("domain") for i in window_interactions if i.get("domain")})
    family_engagement = _summarize_family_engagement(elder_id, cycle_start, cycle_end)

    # WHY: If the elder had no activity this cycle, skip the LLM call entirely and
    # emit a clean "insufficient data" report rather than paying for an empty prompt.
    if not window_interactions and not insights:
        logger.info("No activity for elder %s in cycle %s..%s.", elder_id, cycle_start, cycle_end)
        summary = {
            "engagement_trend": "No interactions were recorded this cycle.",
            "emotional_trend": "No mood signal available this cycle.",
            "recurring_topics": [],
        }
    else:
        summary = generate_weekly_summary(profile, window_interactions, insights)

    record = {
        "elder_id": elder_id,
        "cycle_start": _iso_date(cycle_start),
        "cycle_end": _iso_date(cycle_end),
        "engagement_trend": summary.get("engagement_trend"),
        "emotional_trend": summary.get("emotional_trend"),
        "recurring_topics": summary.get("recurring_topics", []),
        "domains_completed": domains_completed,
        "family_engagement": family_engagement,
    }

    saved = insert_weekly_report(record)
    logger.info("Weekly report stored for elder %s (%s..%s).", elder_id, cycle_start, cycle_end)
    return saved or record
