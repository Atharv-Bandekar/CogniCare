"""
Telegram bot pipeline — the recruiter-facing conversation loop.

Design goals:
  1. Reuse the EXACT agent pipeline the WhatsApp path already uses and tests —
     question engine + Interviewer -> Evaluator -> Coordinator, RAG memory, and
     escalation. The shared, tested helpers are imported from the inbound task
     rather than reimplemented, so the analysis logic stays single-sourced.
  2. Add the two things a live chat needs that the WhatsApp worker lacks:
        - a warm, user-facing reply (agents.companion), and
        - an on-demand conversation loop (ask -> answer -> reply -> ask again),
     instead of one scheduled question a day.
  3. Serve a walk-up stranger: on first contact we auto-provision a "demo" elder
     keyed by the Telegram chat id, so a recruiter needs no onboarding.

Channel-agnostic core: this task consumes the same `inbound` queue and calls the
same agents; only the transport (Telegram vs Twilio) and the elder-resolution key
(chat id vs phone number) differ.
"""
import logging
import os

from backend.celery_app import celery_app
from backend.database.db import (
    get_elder_by_telegram_chat_id,
    insert_elder_profile,
    get_recent_engagement_scores,
    get_interactions_by_elder,
    insert_daily_interaction,
    update_elder_profile,
    update_daily_interaction,
    get_open_interaction_for_elder,
    get_interaction_by_twilio_sid,
    insert_interaction_insight,
    insert_recommendation,
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

# Reuse the WhatsApp pipeline's tested helpers rather than duplicating them.
# (Underscore names are module-private by convention, but importing them keeps
# the analysis logic single-sourced — if inbound.py improves, Telegram inherits it.)
from backend.celery_app.tasks.inbound import (
    _to_english,
    _store_memories,
    _handle_escalation,
    _weather_for,
)

logger = logging.getLogger(__name__)

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi", "ta": "Tamil"}

WELCOME = (
    "Namaste! I'm CogniCare — a warm companion who loves hearing life stories. "
    "Each time we chat I'll ask you a little something. There are no right or wrong "
    "answers; just share whatever comes to mind. Here's my first one \U0001F447"
)

UNCLEAR_AUDIO_REPLY = (
    "Sorry, I couldn't quite hear that. Could you send it once more — either a "
    "voice note or a typed message?"
)

WARMING_UP = "CogniCare is just warming up — please try again in a moment."


# ---------------------------------------------------------------------------
# Elder resolution / auto-provisioning
# ---------------------------------------------------------------------------

def _resolve_or_create_elder(chat_id, first_name: str | None) -> dict | None:
    """
    Finds the elder mapped to this Telegram chat, or provisions a fresh demo elder.

    Returns None (and the caller sends a gentle 'warming up' note) if the lookup
    or insert fails — most commonly because migration 0003 hasn't been run, or
    TELEGRAM_DEMO_CAREGIVER_ID isn't set (it satisfies the NOT NULL caregiver FK).
    """
    try:
        elder = get_elder_by_telegram_chat_id(str(chat_id))
    except Exception as exc:
        logger.error(
            "Telegram elder lookup failed for chat %s (did migration 0003 run?): %s",
            chat_id, exc,
        )
        return None
    if elder:
        return elder

    caregiver_id = os.getenv("TELEGRAM_DEMO_CAREGIVER_ID")
    if not caregiver_id:
        logger.error(
            "TELEGRAM_DEMO_CAREGIVER_ID is not set; cannot auto-provision a demo "
            "elder for chat %s (elder_profiles.caregiver_user_id is NOT NULL).",
            chat_id,
        )
        return None

    # whatsapp_number is NOT NULL UNIQUE in the schema; a Telegram demo elder has
    # no phone, so we store a synthetic, collision-free placeholder.
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
    }
    try:
        elder = insert_elder_profile(profile)
        logger.info("Provisioned Telegram demo elder %s for chat %s.", elder.get("id"), chat_id)
        return elder
    except Exception as exc:
        logger.error("Failed to create Telegram demo elder for chat %s: %s", chat_id, exc)
        return None


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

def _ask_new_question(elder: dict, chat_id) -> bool:
    """
    Builds today's question with the same DDA + RAG context as the WhatsApp
    scheduler, opens an interaction row for the reply to attach to, sends it over
    Telegram, and advances the 7-day domain rotation so consecutive questions vary.

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

    sent = send_telegram_message(chat_id, question)

    try:
        update_elder_profile(elder_id, {"cycle_day": (cycle_day % 7) + 1})
    except Exception as exc:
        logger.warning("Could not advance cycle_day for %s: %s", elder_id, exc)

    return sent is not None


# ---------------------------------------------------------------------------
# Process a reply (mirrors inbound.process_inbound_message, then replies to user)
# ---------------------------------------------------------------------------

def _process_reply(elder: dict, interaction: dict, transcript: str, source: str,
                   external_id: str | None, chat_id) -> dict:
    """
    Runs the full analysis pipeline on the elder's reply, then sends a warm,
    user-facing acknowledgement. Every step degrades gracefully: a failure in
    insight/memory/recommendation must never cost us the reply, which is saved first.
    """
    elder_id = elder["id"]
    interaction_id = interaction["id"]

    # 1. Persist the raw reply against the open interaction.
    try:
        update_daily_interaction(
            interaction_id,
            {
                "raw_response": transcript,
                "transcript_source": source,
                "language": elder.get("preferred_language"),
                "twilio_message_sid": external_id,  # reused column: stores the tg:<chat>:<msg> id
            },
        )
    except Exception as exc:
        logger.error("Failed to attach reply to interaction %s: %s", interaction_id, exc)

    # 2. Normalize to English for analysis (original stays in raw_response).
    analysis_text = _to_english(transcript, elder)

    # 3. Evaluate (Phase 3A contract).
    insight = evaluate_response(analysis_text)

    # 4. Persist the insight.
    try:
        insert_interaction_insight(
            {
                "interaction_id": interaction_id,
                "sentiment_label": insight["sentiment_label"],
                "sentiment_score": insight["sentiment_score"],
                "engagement_level": insight["engagement_level"],
                "engagement_score": insight["engagement_score"],
                "response_depth": insight["response_depth"],
                "topics": insight["topics"],
                "safety_flag": insight["safety_flag"],
            }
        )
    except Exception as exc:
        # No self.retry here (unlike WhatsApp): a retry would re-send messages into
        # a live chat. The reply is already saved, so we log and carry on.
        logger.error("Failed to persist insight for interaction %s: %s", interaction_id, exc)

    # 5. Extract + store long-term memories (best-effort).
    _store_memories(elder_id, analysis_text, insight.get("topics"), interaction_id)

    # 6. Caregiver recommendation (best-effort) — populates the dashboard.
    try:
        recommendation = generate_recommendation(
            elder=elder,
            evaluator_output=insight,
            domain=interaction.get("domain", ""),
            memories=[],
            weather_summary=_weather_for(elder),
        )
        insert_recommendation(
            {
                "elder_id": elder_id,
                "interaction_id": interaction_id,
                "recommendation_text": recommendation.get("recommendation_text"),
                "reason": recommendation.get("reason"),
                "status": "pending",
            }
        )
    except Exception as exc:
        logger.error("Recommendation step failed for elder %s: %s", elder_id, exc)

    # 7. Escalation check (safety flag or sustained low engagement).
    _handle_escalation(elder, insight)

    # 8. The new bit: reply to the user in their language, acknowledging what they
    # said. We pass the ORIGINAL transcript (not the English translation) so the
    # reply speaks to their actual words.
    language = LANGUAGE_NAMES.get((elder.get("preferred_language") or "en").lower(), "English")
    reply = generate_companion_reply(
        elder.get("name", "friend"), language, interaction.get("question", ""), transcript
    )
    send_telegram_message(chat_id, reply)

    return insight


# ---------------------------------------------------------------------------
# Celery entry point
# ---------------------------------------------------------------------------

@celery_app.task(name="backend.celery_app.tasks.telegram_bot.process_telegram_update")
def process_telegram_update(payload: dict):
    """
    Turns one inbound Telegram update into a conversation turn.

    Args:
        payload (dict): {chat_id, message_id, text, voice_file_id, first_name}
            built by the Telegram webhook.

    Returns:
        dict: A short outcome summary for logs/monitoring.

    No auto-retry is configured on purpose: this task sends messages as side
    effects, so a Celery retry would duplicate questions/replies. Instead every
    internal step is defensive, and duplicate *deliveries* from Telegram are
    guarded by the external-id idempotency check below.
    """
    chat_id = payload.get("chat_id")
    if chat_id is None:
        return {"status": "ignored_no_chat"}

    message_id = payload.get("message_id")
    text = payload.get("text") or ""
    first_name = payload.get("first_name")
    external_id = f"tg:{chat_id}:{message_id}" if message_id is not None else None

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

    elder = _resolve_or_create_elder(chat_id, first_name)
    if not elder:
        send_telegram_message(chat_id, WARMING_UP)
        return {"status": "no_elder"}

    send_chat_action(chat_id, "typing")

    is_start = text.strip().lower().startswith("/start")
    open_interaction = None if is_start else get_open_interaction_for_elder(elder["id"])

    # Case A: /start, or there's no pending question to answer -> ask one.
    if is_start or not open_interaction:
        transcript, source = (None, "text") if is_start else _resolve_transcript(payload, elder)
        if is_start:
            send_telegram_message(chat_id, WELCOME)
        elif source == "voice" and not transcript:
            # A voice note arrived but we couldn't transcribe it and have nothing
            # pending; nudge, then still open a fresh question.
            send_telegram_message(chat_id, UNCLEAR_AUDIO_REPLY)
        _ask_new_question(elder, chat_id)
        return {"status": "asked", "elder_id": elder["id"]}

    # Case B: there IS a pending question. Did they actually answer it?
    transcript, source = _resolve_transcript(payload, elder)
    if not transcript:
        if source == "voice":
            send_telegram_message(chat_id, UNCLEAR_AUDIO_REPLY)
        return {"status": "empty_transcript", "source": source}

    insight = _process_reply(elder, open_interaction, transcript, source, external_id, chat_id)

    # Keep the conversation flowing: ask the next question after acknowledging.
    _ask_new_question(elder, chat_id)

    return {
        "status": "processed",
        "elder_id": elder["id"],
        "source": source,
        "engagement_level": insight.get("engagement_level"),
        "sentiment_label": insight.get("sentiment_label"),
    }
