"""
Escalation logic — decides when a caregiver should be gently nudged to check in,
and composes that (non-clinical) nudge.

Phase 3A public contract:
    check_consecutive_negative(elder_id: str, days: int = 3) -> bool
    trigger_escalation_alert(elder_id: str) -> dict

Design notes:
- `check_consecutive_negative` detects a *sustained withdrawal* pattern from the
  engagement trend already exposed by the DB layer (get_recent_engagement_scores).
- Acute, single-message distress is handled upstream at evaluate time via the
  evaluator's `safety_flag` (which the Coordinator turns into an immediate,
  non-clinical check-in suggestion). This module owns the slower trend signal.
- `trigger_escalation_alert` DECIDES what to say; actual delivery over
  WhatsApp/Twilio is Member B infra (see the delivery seam below).

HARD RULE (non-clinical): alert copy never diagnoses. The FORBIDDEN_WORDS guard
enforces this even though the copy is authored statically.
"""
import logging
from typing import Dict, Any

from backend.database.db import get_recent_engagement_scores, get_elder_profile

logger = logging.getLogger(__name__)

# An engagement_score at or below this counts as "low/none" engagement.
# Ties to the evaluator's mapping (low=0.3, none=0.0, medium=0.6): 0.4 captures
# low+none while excluding medium.
LOW_ENGAGEMENT_THRESHOLD = 0.4

# How many recent readings must all be low before we flag sustained withdrawal.
CONSECUTIVE_NEGATIVE_DAYS = 3

# Diagnostic terms the caregiver-facing copy must never contain.
FORBIDDEN_WORDS = ["dementia", "depression", "alzheimer", "cognitive impairment", "diagnose", "clinical"]


def check_consecutive_negative(elder_id: str, days: int = CONSECUTIVE_NEGATIVE_DAYS) -> bool:
    """
    Returns True if the elder's recent engagement has been persistently low.

    We pull the engagement scores recorded over the last `days` days and require
    at least `days` readings, all at/below LOW_ENGAGEMENT_THRESHOLD. Requiring a
    minimum number of readings avoids false alarms from a single quiet day or an
    elder with sparse history.

    Args:
        elder_id (str): Elder profile UUID.
        days (int): Lookback window and minimum number of low readings required.

    Returns:
        bool: True if a caregiver check-in should be advised, else False.
    """
    scores = get_recent_engagement_scores(elder_id, lookback_days=days)

    # WHY: Not enough signal to claim a trend — stay conservative and don't alert.
    if not scores or len(scores) < days:
        logger.info(
            "Escalation check for elder %s: insufficient data (%d readings, need %d).",
            elder_id, len(scores) if scores else 0, days,
        )
        return False

    all_low = all(score <= LOW_ENGAGEMENT_THRESHOLD for score in scores)
    if all_low:
        logger.info(
            "Escalation triggered for elder %s: %d consecutive low-engagement readings.",
            elder_id, len(scores),
        )
    return all_low


def trigger_escalation_alert(elder_id: str) -> dict:
    """
    Composes a gentle, NON-CLINICAL caregiver alert for an elder showing sustained
    low engagement.

    This function decides *what* to say and returns a structured alert payload.
    It does not send anything itself — delivery over WhatsApp/Twilio (and any
    persistence to an escalations table) is Member B / infra responsibility.

    Args:
        elder_id (str): Elder profile UUID.

    Returns:
        dict: {
            elder_id, caregiver_user_id, alert_type, severity,
            message, requires_delivery
        }
    """
    profile = get_elder_profile(elder_id) or {}
    name = profile.get("name") or "your loved one"
    caregiver_user_id = profile.get("caregiver_user_id")

    message = (
        f"We noticed {name} has been a little quieter than usual in their recent "
        f"check-ins. It might be a lovely time to give them a call or drop by to "
        f"see how they're doing."
    )

    # GUARDRAIL: defense-in-depth non-clinical check on caregiver-facing copy.
    lowered = message.lower()
    if any(word in lowered for word in FORBIDDEN_WORDS):
        logger.warning("Escalation copy tripped the non-clinical guard; using safe fallback.")
        message = (
            "We noticed things have been a little quieter than usual lately. "
            "It might be a nice time to check in with a call or a visit."
        )

    alert = {
        "elder_id": elder_id,
        "caregiver_user_id": caregiver_user_id,
        "alert_type": "consecutive_low_engagement",
        "severity": "advisory",
        "message": message,
        # Signals the pipeline that this still needs to be delivered to the caregiver.
        "requires_delivery": True,
    }

    logger.warning("Escalation alert composed for elder %s (caregiver %s).", elder_id, caregiver_user_id)

    # TODO(@member-b / infra): deliver `alert["message"]` to the caregiver over
    # WhatsApp (Twilio) and record the escalation. Expected seam:
    #     send_caregiver_notification(caregiver_user_id, alert["message"])
    return alert
