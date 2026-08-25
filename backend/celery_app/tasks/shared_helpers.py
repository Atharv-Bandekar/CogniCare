"""
Shared helpers for inbound message processing (Telegram and legacy WhatsApp).

Extracted from inbound.py to avoid circular dependencies and allow Telegram-only
deployment without WhatsApp code.
"""
import logging

from backend.database.db import (
    get_elder_by_telegram_user_id,
    insert_interaction_insight,
    insert_recommendation,
)
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


def to_english(text: str, elder: dict) -> str:
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


def store_memories(elder_id: str, transcript: str, topics: list, interaction_id: str) -> int:
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


def weather_for(elder: dict) -> str:
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


def handle_escalation(elder: dict, insight: dict) -> bool:
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
        # alerts are surfaced through the dashboard only.
        # (Telegram production would need a caregiver Telegram user_id field)
        logger.info(
            "Escalation alert composed for elder %s; surfaced via dashboard only.", elder_id
        )
        return True
    except Exception as exc:
        logger.error("Escalation handling failed for elder %s: %s", elder_id, exc)
        return False


def process_reply_pipeline(
    elder: dict,
    interaction: dict,
    transcript: str,
    source: str,
    external_id: str | None,
    chat_id: int | str,
    send_reply_fn
) -> dict:
    """
    Core reply processing pipeline shared by Telegram and WhatsApp.

    Args:
        elder: Elder profile dict
        interaction: Open daily_interaction row
        transcript: User's reply text
        source: 'voice' or 'text'
        external_id: Idempotency key (MessageSid or tg:<chat>:<msg>)
        chat_id: Telegram chat_id or WhatsApp number
        send_reply_fn: Function to send reply message (Telegram or WhatsApp)

    Returns:
        insight dict from evaluator
    """
    elder_id = elder["id"]
    interaction_id = interaction["id"]

    # 1. Persist the raw reply against the open interaction.
    try:
        from backend.database.db import update_daily_interaction
        update_daily_interaction(
            interaction_id,
            {
                "raw_response": transcript,
                "transcript_source": source,
                "language": elder.get("preferred_language"),
                "twilio_message_sid": external_id,  # reused column for idempotency
            },
        )
    except Exception as exc:
        logger.error("Failed to attach reply to interaction %s: %s", interaction_id, exc)

    # 2. Normalize to English for analysis (original stays in raw_response).
    analysis_text = to_english(transcript, elder)

    # 3. Evaluate (Phase 3A contract).
    insight = evaluate_response(analysis_text)

    # 4. Persist the insight against the interaction.
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
        logger.error("Failed to persist insight for interaction %s: %s", interaction_id, exc)

    # 5. Extract and store long-term memories (best-effort).
    store_memories(elder_id, analysis_text, insight.get("topics"), interaction_id)

    # 6. Generate the caregiver recommendation.
    try:
        recommendation = generate_recommendation(
            elder=elder,
            evaluator_output=insight,
            domain=interaction.get("domain", ""),
            memories=[],
            weather_summary=weather_for(elder),
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

    # 7. Escalation check (immediate safety flag or sustained low engagement).
    handle_escalation(elder, insight)

    # 8. Send companion reply (Telegram only — WhatsApp doesn't reply to elder)
    if send_reply_fn:
        from backend.agents.companion import generate_companion_reply
        language = LANGUAGE_NAMES.get((elder.get("preferred_language") or "en").lower(), "English")
        reply = generate_companion_reply(
            elder.get("name", "friend"), language, interaction.get("question", ""), transcript
        )
        send_reply_fn(chat_id, reply)

    return insight