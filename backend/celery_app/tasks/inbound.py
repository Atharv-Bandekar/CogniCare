"""
Background tasks for processing inbound WhatsApp messages.

This is the core async pipeline (Phase 3B). For each inbound message:

    1. Idempotency guard on Twilio MessageSid
    2. Resolve the elder from the sender's WhatsApp number
    3. Obtain a transcript (Whisper for voice notes, Body for text)
    4. Translate to English for analysis if the elder writes another language
    5. Attach the reply to the open interaction row
    6. Evaluate it            -> backend.agents.evaluator.evaluate_response
    7. Persist the insight    -> interaction_insights
    8. Extract + store memories (RAG)
    9. Generate a caregiver recommendation -> backend.agents.coordinator
   10. Escalate if needed     -> backend.agents.escalation

Design notes:
- The webhook must return in <5s, so everything expensive lives here.
- Each external step degrades gracefully: a failure in memories, weather, or the
  recommendation must never cost us the elder's response, which is already safely
  persisted by step 5.
"""
import logging

from backend.celery_app import celery_app
from backend.database.db import (
    get_interaction_by_twilio_sid,
    get_elder_by_whatsapp_number,
    get_open_interaction_for_elder,
    update_daily_interaction,
    insert_interaction_insight,
    insert_recommendation,
)
from backend.integrations.twilio_client import download_media, send_whatsapp_message
from backend.integrations.stt import transcribe_audio
from backend.agents.evaluator import evaluate_response
from backend.agents.coordinator import generate_recommendation
from backend.agents.escalation import check_consecutive_negative, trigger_escalation_alert
from backend.agents.base import translate_to_english
from backend.rag.memory_extraction import extract_memorable_content
from backend.rag.memory_store import store_memory
from backend.integrations.weather import get_weather_summary

logger = logging.getLogger(__name__)

# Full language names for the translation helper, keyed by profile language code.
LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "mr": "Marathi", "ta": "Tamil"}

# Sent when a voice note can't be transcribed, so the elder isn't left in silence.
UNCLEAR_AUDIO_REPLY = (
    "Sorry, I couldn't quite hear that. Could you send it once more, "
    "either as a voice note or a message?"
)


def _resolve_transcript(payload: dict, elder: dict) -> tuple[str | None, str]:
    """
    Produces (transcript, source) where source is 'voice' or 'text'.

    Voice notes are downloaded from Twilio and sent through Whisper; text bodies
    are used directly.
    """
    media_url = payload.get("MediaUrl0")
    if media_url:
        audio = download_media(media_url)
        if not audio:
            return None, "voice"
        transcript = transcribe_audio(audio, language=elder.get("preferred_language"))
        return transcript, "voice"

    body = (payload.get("Body") or "").strip()
    return (body or None), "text"


def _to_english(text: str, elder: dict) -> str:
    """
    Normalizes the transcript to English for analysis.

    WHY: The evaluator's sentiment lexicon and the memory extractor both reason in
    English. Elders may reply in Hindi/Marathi/Tamil (native script or romanized),
    so we translate before analysis while the original stays stored in raw_response.
    """
    language_code = (elder.get("preferred_language") or "en").lower()
    if language_code.startswith("en"):
        return text
    language_name = LANGUAGE_NAMES.get(language_code, "English")
    try:
        return translate_to_english(text, language_name) or text
    except Exception as exc:
        logger.warning("Translation failed, analyzing original text: %s", exc)
        return text


def _store_memories(elder_id: str, transcript: str, topics: list, interaction_id: str) -> int:
    """Extracts and persists long-term memories. Returns the number stored."""
    stored = 0
    try:
        memories = extract_memorable_content(transcript, topics or []) or []
    except Exception as exc:
        logger.error("Memory extraction failed for elder %s: %s", elder_id, exc)
        return 0

    for memory in memories:
        content = (memory or {}).get("content")
        category = (memory or {}).get("category")
        if not content or not category:
            continue
        try:
            store_memory(elder_id, content, category, interaction_id)
            stored += 1
        except Exception as exc:
            # WHY: One bad embedding shouldn't discard the remaining memories.
            logger.error("Failed to store a memory for elder %s: %s", elder_id, exc)
    return stored


def _weather_for(elder: dict) -> str:
    """Best-effort weather lookup; the coordinator treats 'normal' as a safe default."""
    context = elder.get("personal_context") or {}
    lat, lon = context.get("lat"), context.get("lon")
    if lat is None or lon is None:
        return "normal"
    try:
        return get_weather_summary(lat, lon)
    except Exception as exc:
        logger.warning("Weather lookup failed: %s", exc)
        return "normal"


def _handle_escalation(elder: dict, insight: dict) -> bool:
    """
    Decides whether to alert the caregiver and delivers the alert if possible.

    Two triggers:
      - immediate: the evaluator raised a (non-clinical) safety_flag
      - trend:     sustained low engagement across recent days
    """
    elder_id = elder["id"]
    try:
        immediate = bool(insight.get("safety_flag"))
        trend = check_consecutive_negative(elder_id)
        if not (immediate or trend):
            return False

        alert = trigger_escalation_alert(elder_id)
        reason = "safety_flag" if immediate else "consecutive_low_engagement"
        logger.warning("Escalation for elder %s (reason=%s).", elder_id, reason)

        # NOTE: the schema links a caregiver via caregiver_user_id (auth.users) and
        # stores no caregiver phone number. Until a dedicated contact column exists,
        # an optional personal_context.caregiver_whatsapp enables WhatsApp delivery;
        # otherwise the alert is surfaced through the dashboard only.
        caregiver_number = ((elder.get("personal_context") or {}).get("caregiver_whatsapp") or "").strip()
        if caregiver_number:
            send_whatsapp_message(caregiver_number, alert["message"])
        else:
            logger.info(
                "Escalation alert composed for elder %s but no caregiver WhatsApp number is on "
                "file; surfaced via dashboard only.", elder_id
            )
        return True
    except Exception as exc:
        logger.error("Escalation handling failed for elder %s: %s", elder_id, exc)
        return False


@celery_app.task(
    bind=True,
    name="backend.celery_app.tasks.inbound.process_inbound_message",
    max_retries=3,
    default_retry_delay=60,
)
def process_inbound_message(self, payload: dict):
    """
    Core async worker: turns an inbound WhatsApp message into an insight,
    memories, a caregiver recommendation, and (if warranted) an escalation.

    Args:
        payload (dict): {From, Body, MediaUrl0, MessageSid} from the Twilio webhook.

    Returns:
        dict: A summary of what the pipeline did (useful for logs/monitoring).
    """
    message_sid = payload.get("MessageSid")
    from_number = payload.get("From")

    # 1. Idempotency — Twilio retries webhooks, so never double-process a SID.
    if message_sid and get_interaction_by_twilio_sid(message_sid):
        logger.info("Duplicate MessageSid %s; skipping.", message_sid)
        return {"status": "duplicate", "message_sid": message_sid}

    # 2. Identify the sender.
    elder = get_elder_by_whatsapp_number(from_number)
    if not elder:
        logger.warning("Inbound message from unknown number; ignoring.")
        return {"status": "unknown_sender"}

    elder_id = elder["id"]

    # 3. Transcript (voice note or text).
    transcript, source = _resolve_transcript(payload, elder)
    if not transcript:
        logger.info("No usable transcript for elder %s (source=%s).", elder_id, source)
        if source == "voice":
            send_whatsapp_message(from_number, UNCLEAR_AUDIO_REPLY)
        return {"status": "empty_transcript", "source": source}

    # 4. Attach the reply to the open interaction (the question we asked).
    interaction = get_open_interaction_for_elder(elder_id)
    if not interaction:
        # Unsolicited message — logged rather than dropped silently, but there's no
        # question to attach it to, so we don't fabricate an interaction row.
        logger.info("No open interaction for elder %s; treating as unsolicited.", elder_id)
        return {"status": "no_open_interaction", "transcript_length": len(transcript)}

    interaction_id = interaction["id"]
    update_daily_interaction(
        interaction_id,
        {
            "raw_response": transcript,
            "transcript_source": source,
            "language": elder.get("preferred_language"),
            "twilio_message_sid": message_sid,
        },
    )

    # 5. Normalize to English for analysis (original stays in raw_response).
    analysis_text = _to_english(transcript, elder)

    # 6. Evaluate (Phase 3A contract).
    insight = evaluate_response(analysis_text)

    # 7. Persist the insight against the interaction.
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
        # Retryable: the response is already saved, so a retry re-analyzes
        # rather than losing the elder's answer.
        logger.error("Failed to persist insight for interaction %s: %s", interaction_id, exc)
        raise self.retry(exc=exc)

    # 8. Extract and store long-term memories (best-effort).
    memories_stored = _store_memories(elder_id, analysis_text, insight.get("topics"), interaction_id)

    # 9. Generate the caregiver recommendation.
    recommendation = None
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

    # 10. Escalation check (immediate safety flag or sustained low engagement).
    escalated = _handle_escalation(elder, insight)

    logger.info(
        "Processed inbound for elder %s: engagement=%s sentiment=%s memories=%d escalated=%s",
        elder_id, insight["engagement_level"], insight["sentiment_label"], memories_stored, escalated,
    )

    return {
        "status": "processed",
        "elder_id": elder_id,
        "interaction_id": interaction_id,
        "source": source,
        "engagement_level": insight["engagement_level"],
        "sentiment_label": insight["sentiment_label"],
        "memories_stored": memories_stored,
        "recommendation_created": recommendation is not None,
        "escalated": escalated,
    }
