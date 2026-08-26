"""
Telegram bot pipeline — supports BOTH channels:

1. RECRUITER DEMO (auto-provisioned): Walk-up stranger taps t.me/YourBot → /start
   → auto-provisions demo elder keyed by telegram_chat_id (onboarding_method='demo')

2. PRODUCTION ELDER (deep-link): Caregiver creates elder → gets t.me/YourBot?start=elder_<uuid>
   → elder taps → bot receives /start elder_<uuid> → links telegram_user_id to elder
   → onboarding_method='production', no auto-provisioning

Channel-agnostic core: this task consumes the same `inbound` queue and calls the
same agents; only the transport (Telegram vs Twilio) and the elder-resolution key
(user_id vs chat_id vs phone number) differ.
"""
import logging
import os
import re

from backend.celery_app import celery_app
from backend.database.db import (
    get_elder_by_telegram_chat_id,
    get_elder_by_telegram_user_id,
    link_elder_to_telegram_user,
    insert_elder_profile,
    get_recent_engagement_scores,
    get_interactions_by_elder,
    insert_daily_interaction,
    update_elder_profile,
    update_daily_interaction,
    get_open_interaction_for_elder,
    get_interaction_by_twilio_sid,
)
from backend.agents.question_engine import build_question_context, get_todays_domain
from backend.agents.interviewer import InterviewerAgent
from backend.agents.evaluator import evaluate_response
from backend.agents.coordinator import generate_recommendation
from backend.agents.companion import generate_companion_reply
from backend.integrations.telegram_client import (
    send_telegram_message,
    send_chat_action,
    download_telegram_voice,
)
from backend.integrations.stt import transcribe_audio

# Shared pipeline helpers (Telegram + legacy WhatsApp)
from backend.celery_app.tasks.shared_helpers import (
    to_english,
    store_memories,
    handle_escalation,
    weather_for,
    process_reply_pipeline,
    LANGUAGE_NAMES,
)

logger = logging.getLogger(__name__)

WELCOME = (
    "Namaste! I'm CogniCare — a warm companion who loves hearing life stories. "
    "Each time we chat I'll ask you a little something. There are no right or wrong "
    "answers; just share whatever comes to mind. Here's my first one \U0001F447"
)

WELCOME_PRODUCTION = (
    "Namaste! Welcome to CogniCare. Your caregiver has set up daily memory questions "
    "for you. Here's your first one \U0001F447"
)

UNCLEAR_AUDIO_REPLY = (
    "Sorry, I couldn't quite hear that. Could you send it once more — either a "
    "voice note or a typed message?"
)

WARMING_UP = "CogniCare is just warming up — please try again in a moment."

DEEP_LINK_PATTERN = re.compile(r"^/start\s+elder_([a-f0-9-]{36})$", re.IGNORECASE)


# ---------------------------------------------------------------------------
# Elder resolution — dual mode: DEMO (chat_id) vs PRODUCTION (user_id + deep-link)
# ---------------------------------------------------------------------------

def _resolve_elder(
    chat_id: int | str,
    user_id: int | str,
    first_name: str | None,
    start_param: str | None = None
) -> tuple[dict | None, str]:
    """
    Resolves an elder for this Telegram user.

    Returns:
        (elder_dict | None, mode) where mode is 'demo' | 'production' | 'error'

    Logic:
    1. If /start elder_<uuid> → production onboarding: link user_id to that elder
    2. Else if user has telegram_user_id → production elder (return it)
    3. Else if chat has telegram_chat_id → demo elder (return it)
    4. Else → auto-provision demo elder (recruiter walk-up)
    """
    # 1. Production deep-link onboarding: /start elder_<uuid>
    if start_param:
        match = DEEP_LINK_PATTERN.match(start_param)
        if match:
            elder_id = match.group(1)
            logger.info("Production onboarding: linking user %s to elder %s", user_id, elder_id)
            try:
                elder = link_elder_to_telegram_user(elder_id, user_id)
                logger.info("Successfully linked elder %s to Telegram user %s", elder_id, user_id)
                return elder, 'production'
            except Exception as exc:
                logger.error("Failed to link elder %s to user %s: %s", elder_id, user_id, exc)
                return None, 'error'

    # 2. Existing production elder (linked via user_id)
    try:
        elder = get_elder_by_telegram_user_id(user_id)
        if elder:
            logger.debug("Found production elder %s for user %s", elder.get('id'), user_id)
            return elder, 'production'
    except Exception as exc:
        logger.warning("Telegram production elder lookup failed for user %s: %s", user_id, exc)

    # 3. Existing demo elder (linked via chat_id)
    try:
        elder = get_elder_by_telegram_chat_id(str(chat_id))
        if elder:
            logger.debug("Found demo elder %s for chat %s", elder.get('id'), chat_id)
            return elder, 'demo'
    except Exception as exc:
        logger.warning("Telegram demo elder lookup failed for chat %s: %s", chat_id, exc)

    # 4. Auto-provision demo elder (recruiter walk-up)
    caregiver_id = os.getenv("TELEGRAM_DEMO_CAREGIVER_ID")
    if not caregiver_id:
        logger.error(
            "TELEGRAM_DEMO_CAREGIVER_ID not set; cannot auto-provision demo elder for chat %s",
            chat_id,
        )
        return None, 'error'

    profile = {
        "caregiver_user_id": caregiver_id,
        "name": (first_name or "Friend").strip()[:80] or "Friend",
        "whatsapp_number": f"tg:{chat_id}",
        "preferred_language": "en",
        "preferred_interaction_time": "09:00",
        "timezone": "Asia/Kolkata",
        "proximity": "remote",
        "personal_context": {"source": "telegram_demo", "telegram_first_name": first_name},
        "cycle_day": 1,
        "telegram_chat_id": str(chat_id),
        "onboarding_method": "demo",
    }
    try:
        elder = insert_elder_profile(profile)
        logger.info("Provisioned Telegram demo elder %s for chat %s.", elder.get("id"), chat_id)
        return elder, 'demo'
    except Exception as exc:
        logger.error("Failed to create Telegram demo elder for chat %s: %s", chat_id, exc)
        return None, 'error'


# ---------------------------------------------------------------------------
# Transcript (text or voice note)
# ---------------------------------------------------------------------------

def _resolve_transcript(payload: dict, elder: dict) -> tuple[str | None, str]:
    """Returns (transcript, source) where source is 'voice' or 'text'."""
    voice_file_id = payload.get("voice_file_id")
    if voice_file_id:
        audio = download_telegram_voice(voice_file_id)
        if not audio:
            return None, "voice"
        transcript = transcribe_audio(audio, language=elder.get("preferred_language"))
        return transcript, "voice"

    text = (payload.get("text") or "").strip()
    return (text or None), "text"


# ---------------------------------------------------------------------------
# Ask a question (mirrors scheduling.send_daily_question, delivered via Telegram)
# ---------------------------------------------------------------------------

def _ask_new_question(elder: dict, chat_id, mode: str) -> bool:
    """
    Builds today's question with the same DDA + RAG context as the WhatsApp
    scheduler, opens an interaction row for the reply to attach to, sends it over
    Telegram, and advances the 7-day domain rotation so consecutive questions vary.

    Args:
        elder: Elder profile dict
        chat_id: Telegram chat ID
        mode: 'demo' or 'production' — determines welcome message

    Returns True if a question was sent.
    """
    elder_id = elder["id"]
    cycle_day = elder.get("cycle_day") or 1
    domain_key, _ = get_todays_domain(cycle_day)

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
        context = {
            "domain_description": "",
            "difficulty": "medium",
            "personal_context_summary": context_summary,
            "retrieved_memories": [],
        }

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

    # Open the interaction row BEFORE sending, so the elder's reply has a row to
    # attach to (same ordering as the WhatsApp scheduler).
    try:
        insert_daily_interaction({"elder_id": elder_id, "domain": domain_key, "question": question})
    except Exception as exc:
        logger.error("Failed to open interaction for elder %s: %s", elder_id, exc)

    # For on-demand questions (via /start), use the chat_id from the payload
    # Production elders: chat_id == user_id (private chat)
    # Demo elders: chat_id is the chat they started
    sent = send_telegram_message(chat_id, question)

    try:
        update_elder_profile(elder_id, {"cycle_day": (cycle_day % 7) + 1})
    except Exception as exc:
        logger.warning("Could not advance cycle_day for %s: %s", elder_id, exc)

    return sent is not None


# ---------------------------------------------------------------------------
# Celery entry point
# ---------------------------------------------------------------------------

@celery_app.task(name="backend.celery_app.tasks.telegram_bot.process_telegram_update")
def process_telegram_update(payload: dict):
    """
    Turns one inbound Telegram update into a conversation turn.

    Args:
        payload (dict): {chat_id, message_id, text, voice_file_id, first_name, user_id}
            built by the Telegram webhook.

    Returns:
        dict: A short outcome summary for logs/monitoring.

    No auto-retry is configured on purpose: this task sends messages as side
    effects, so a Celery retry would duplicate questions/replies. Instead every
    internal step is defensive, and duplicate *deliveries* from Telegram are
    guarded by the external-id idempotency check below.
    """
    chat_id = payload.get("chat_id")
    user_id = payload.get("user_id")
    if chat_id is None or user_id is None:
        return {"status": "ignored_no_chat_or_user"}

    message_id = payload.get("message_id")
    text = payload.get("text") or ""
    first_name = payload.get("first_name")
    external_id = f"tg:{chat_id}:{message_id}" if message_id is not None else None

    # Extract deep-link parameter from /start elder_<uuid>
    start_param = text.strip() if text.strip().lower().startswith("/start") else None

    # Idempotency: Telegram re-delivers an update if the webhook didn't 200 in
    # time. We stamp external_id onto the interaction when a reply is processed,
    # so a re-delivery of that same message is a no-op.
    if external_id:
        try:
            if get_interaction_by_twilio_sid(external_id):
                logger.info("Duplicate Telegram update %s; skipping.", external_id)
                return {"status": "duplicate", "external_id": external_id}
        except Exception:
            pass  # a lookup hiccup shouldn't block the conversation

    # Resolve elder (handles both demo and production)
    elder, mode = _resolve_elder(chat_id, user_id, first_name, start_param)
    if not elder:
        send_telegram_message(chat_id, WARMING_UP)
        return {"status": "no_elder", "mode": mode}

    send_chat_action(chat_id, "typing")

    is_start = text.strip().lower().startswith("/start")
    open_interaction = None if is_start else get_open_interaction_for_elder(elder["id"])

    # Case A: /start, or there's no pending question to answer -> ask one.
    if is_start or not open_interaction:
        transcript, source = (None, "text") if is_start else _resolve_transcript(payload, elder)
        if is_start:
            # Different welcome for demo vs production
            welcome_msg = WELCOME_PRODUCTION if mode == 'production' else WELCOME
            send_telegram_message(chat_id, welcome_msg)
        elif source == "voice" and not transcript:
            # A voice note arrived but we couldn't transcribe it and have nothing
            # pending; nudge, then still open a fresh question.
            send_telegram_message(chat_id, UNCLEAR_AUDIO_REPLY)
        _ask_new_question(elder, chat_id, mode)
        return {"status": "asked", "elder_id": elder["id"], "mode": mode}

    # Case B: there IS a pending question. Did they actually answer it?
    transcript, source = _resolve_transcript(payload, elder)
    if not transcript:
        if source == "voice":
            send_telegram_message(chat_id, UNCLEAR_AUDIO_REPLY)
        return {"status": "empty_transcript", "source": source, "mode": mode}

    # Use shared pipeline (includes companion reply)
    def send_reply(chat_id, text):
        send_telegram_message(chat_id, text)

    insight = process_reply_pipeline(
        elder=elder,
        interaction=open_interaction,
        transcript=transcript,
        source=source,
        external_id=external_id,
        chat_id=chat_id,
        send_reply_fn=send_reply
    )

    # Keep the conversation flowing: ask the next question after acknowledging.
    _ask_new_question(elder, chat_id, mode)

    return {
        "status": "processed",
        "elder_id": elder["id"],
        "source": source,
        "mode": mode,
        "engagement_level": insight.get("engagement_level"),
        "sentiment_label": insight.get("sentiment_label"),
    }
