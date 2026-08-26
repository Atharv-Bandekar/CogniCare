"""
Scheduling tasks: sending each elder their daily question at their preferred local time.

Two tasks:
    dispatch_daily_questions()   — beat-driven fan-out; finds elders due right now
    send_daily_question(elder_id) — builds and sends one elder's question (Telegram)

WHY the fan-out split: one elder's LLM/Telegram failure must not block everyone
else's daily question, and per-elder tasks retry independently.
"""
import logging
import os
from datetime import datetime, timezone, timedelta

from backend.celery_app import celery_app
from backend.database.db import (
    get_all_elders,
    get_elder_profile,
    get_recent_engagement_scores,
    get_interactions_by_elder,
    insert_daily_interaction,
    update_elder_profile,
    get_unincorporated_family_suggestion,
    mark_family_suggestion_incorporated,
)
from backend.agents.question_engine import build_question_context, get_todays_domain
from backend.agents.interviewer import InterviewerAgent
from backend.integrations.telegram_client import send_telegram_message

logger = logging.getLogger(__name__)

# Beat runs this every 15 minutes; an elder is "due" if their preferred time falls
# within the window that just elapsed. Keeps sends close to the chosen time
# without needing a per-elder cron entry.
DISPATCH_WINDOW_MINUTES = 15

# Full language names for the Interviewer prompt, keyed by profile language code.
LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi", "ta": "Tamil"}

# Fixed offsets avoid a hard dependency on a tzdata package in the worker image.
# Asia/Kolkata is the product default; extend as new regions are supported.
_TZ_OFFSETS = {
    "Asia/Kolkata": timedelta(hours=5, minutes=30),
    "Asia/Calcutta": timedelta(hours=5, minutes=30),
    "UTC": timedelta(0),
}


def _local_now(tz_name: str) -> datetime:
    """Current local time for a timezone name, falling back to Asia/Kolkata."""
    offset = _TZ_OFFSETS.get(tz_name or "", _TZ_OFFSETS["Asia/Kolkata"])
    return datetime.now(timezone.utc) + offset


def _parse_time_to_minutes(value) -> int | None:
    """Parses a 'HH:MM' / 'HH:MM:SS' time (or time object) into minutes since midnight."""
    if value is None:
        return None
    if hasattr(value, "hour") and hasattr(value, "minute"):
        return value.hour * 60 + value.minute
    parts = str(value).strip().split(":")
    try:
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, IndexError):
        logger.warning("Unparseable preferred_interaction_time: %r", value)
        return None


def is_elder_due(elder: dict, window_minutes: int = DISPATCH_WINDOW_MINUTES, now: datetime | None = None) -> bool:
    """
    True if the elder's preferred interaction time falls in the window ending now.

    Args:
        elder (dict): Elder profile (uses preferred_interaction_time, timezone).
        window_minutes (int): Size of the just-elapsed window.
        now (datetime | None): Override for local "now" (tests).

    WHY exposed as a pure function: the due-time arithmetic is the fiddliest part
    of scheduling, so it's unit-testable without Celery or a database.
    """
    target = _parse_time_to_minutes(elder.get("preferred_interaction_time"))
    if target is None:
        return False

    local_now = now or _local_now(elder.get("timezone"))
    current = local_now.hour * 60 + local_now.minute

    # Half-open window (start, current]: each sweep owns exactly `window_minutes`
    # distinct minutes, so consecutive sweeps never overlap and never leave a gap.
    #
    # WHY half-open matters: with an inclusive start, a preferred time landing on a
    # window boundary (09:00, 08:45 — the round times people actually pick) matches
    # both the 09:00 and the 09:15 sweep, and the elder gets two questions a day.
    start = (current - window_minutes) % (24 * 60)
    if start < current:
        return start < target <= current
    # Window spans midnight
    return target > start or target <= current


@celery_app.task(name="backend.celery_app.tasks.scheduling.dispatch_daily_questions")
def dispatch_daily_questions():
    """
    Beat entry point. Finds every elder whose preferred time just passed and queues
    an individual send task for each.

    Returns:
        dict: {"checked": int, "queued": int}
    """
    try:
        elders = get_all_elders() or []
    except Exception as exc:
        logger.error("Could not load elders for dispatch: %s", exc)
        return {"checked": 0, "queued": 0}

    queued = 0
    for elder in elders:
        try:
            if is_elder_due(elder):
                send_daily_question.apply_async(args=[elder["id"]], queue="scheduling")
                queued += 1
        except Exception as exc:
            logger.error("Failed to queue daily question for %s: %s", elder.get("id"), exc)

    logger.info("Daily dispatch: checked %d elders, queued %d.", len(elders), queued)
    return {"checked": len(elders), "queued": queued}


@celery_app.task(
    bind=True,
    name="backend.celery_app.tasks.scheduling.send_daily_question",
    max_retries=2,
    default_retry_delay=300,
)
def send_daily_question(self, elder_id: str):
    """
    Builds today's question for one elder, sends it over Telegram, records the
    interaction, and advances the 7-day cognitive rotation.

    Production elders: send to their telegram_chat_id (linked via deep-link).
    Demo elders: send to their telegram_chat_id (auto-provisioned).

    Returns:
        dict: Outcome summary including the domain used.
    """
    elder = get_elder_profile(elder_id)
    if not elder:
        logger.warning("send_daily_question: elder %s not found.", elder_id)
        return {"status": "elder_not_found"}

    cycle_day = elder.get("cycle_day") or 1
    domain_key, _ = get_todays_domain(cycle_day)

    # DDA inputs + RAG context for the question.
    try:
        engagement_scores = get_recent_engagement_scores(elder_id, lookback_days=3) or []
    except Exception as exc:
        logger.warning("Could not load engagement scores for %s: %s", elder_id, exc)
        engagement_scores = []

    personal_context = elder.get("personal_context") or {}
    context_summary = ", ".join(f"{k}: {v}" for k, v in personal_context.items()) or "No additional context."

    try:
        context = build_question_context(elder_id, cycle_day, context_summary, engagement_scores)
    except Exception as exc:
        logger.error("Failed to build question context for %s: %s", elder_id, exc)
        raise self.retry(exc=exc)

    # Weave in a pending caregiver suggestion, if one is waiting.
    family_suggestion = None
    try:
        family_suggestion = get_unincorporated_family_suggestion(elder_id)
        if family_suggestion:
            context["pending_family_context"] = family_suggestion.get("caregiver_suggestion")
    except Exception as exc:
        logger.warning("Could not fetch family suggestion for %s: %s", elder_id, exc)

    # Avoid repeating recent questions.
    try:
        recent = get_interactions_by_elder(elder_id, limit=5) or []
        past_questions = [i.get("question") for i in reversed(recent) if i.get("question")]
    except Exception:
        past_questions = []

    language = LANGUAGE_NAMES.get((elder.get("preferred_language") or "en").lower(), "English")
    question = InterviewerAgent().generate_question(
        elder_name=elder.get("name", "friend"),
        language=language,
        context=context,
        past_questions=past_questions,
    )

    # Record the interaction BEFORE sending: if the send fails we still know what
    # was asked, and the inbound worker has an open row to attach a reply to.
    interaction = insert_daily_interaction(
        {
            "elder_id": elder_id,
            "domain": domain_key,
            "question": question,
        }
    )
    interaction_id = (interaction or {}).get("id")

    # Send via Telegram (freeform, no template needed)
    # Production elders: use telegram_user_id (private chat = user_id)
    # Demo elders: use telegram_chat_id (auto-provisioned)
    chat_id = elder.get("telegram_user_id") or elder.get("telegram_chat_id")
    if not chat_id:
        logger.error("Elder %s has no telegram_user_id or telegram_chat_id; cannot send daily question.", elder_id)
        raise self.retry(exc=RuntimeError("No Telegram ID for elder"))

    sent = send_telegram_message(chat_id, question)
    if sent is None:
        logger.error("Telegram send failed for elder %s; will retry.", elder_id)
        raise self.retry(exc=RuntimeError("Telegram send failed"))

    # Mark the caregiver suggestion as used, now that it's actually in a question.
    if family_suggestion and interaction_id:
        try:
            mark_family_suggestion_incorporated(family_suggestion["id"], interaction_id)
        except Exception as exc:
            logger.warning("Could not mark family suggestion incorporated: %s", exc)

    # Advance the 7-day rotation (1..7 wraparound).
    try:
        update_elder_profile(elder_id, {"cycle_day": (cycle_day % 7) + 1})
    except Exception as exc:
        logger.warning("Could not advance cycle_day for %s: %s", elder_id, exc)

    logger.info("Sent daily question to elder %s (domain=%s).", elder_id, domain_key)
    return {
        "status": "sent",
        "elder_id": elder_id,
        "interaction_id": interaction_id,
        "domain": domain_key,
        "family_suggestion_used": bool(family_suggestion),
    }
