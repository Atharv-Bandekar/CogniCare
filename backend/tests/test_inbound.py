"""
Tests for the inbound WhatsApp pipeline (Phase 3B).

Every external dependency is patched, so these tests assert the *orchestration*:
idempotency, sender resolution, voice vs text, graceful degradation, and escalation.
"""
import contextlib
import types

import pytest
from unittest.mock import patch

from backend.celery_app.tasks.inbound import process_inbound_message, UNCLEAR_AUDIO_REPLY

MODULE = "backend.celery_app.tasks.inbound"


class Effect:
    """Marker: patch with side_effect instead of return_value."""

    def __init__(self, value):
        self.value = value


ELDER = {
    "id": "elder-1",
    "name": "Arthur",
    "whatsapp_number": "+919000000001",
    "preferred_language": "en",
    "personal_context": {},
}

OPEN_INTERACTION = {"id": "interaction-1", "domain": "episodic_memory"}

INSIGHT = {
    "sentiment_label": "positive",
    "sentiment_score": 0.6,
    "engagement_level": "high",
    "engagement_score": 0.9,
    "response_depth": "deep",
    "topics": ["gardening", "grandchildren"],
    "safety_flag": False,
}

TEXT_PAYLOAD = {
    "From": "whatsapp:+919000000001",
    "Body": "I spent the whole morning in the garden with my grandchildren.",
    "MediaUrl0": None,
    "MessageSid": "SM123",
}

VOICE_PAYLOAD = {
    "From": "whatsapp:+919000000001",
    "Body": "",
    "MediaUrl0": "https://api.twilio.com/media/ME1",
    "MessageSid": "SM124",
}

# Defaults describe the happy path; each test overrides only what it exercises.
DEFAULTS = {
    "get_interaction_by_twilio_sid": None,
    "get_elder_by_whatsapp_number": ELDER,
    "get_open_interaction_for_elder": OPEN_INTERACTION,
    "update_daily_interaction": {"id": "interaction-1"},
    "insert_interaction_insight": {"id": "insight-1"},
    "insert_recommendation": {"id": "rec-1"},
    "download_media": b"fake-ogg-bytes",
    "transcribe_audio": "I walked to the temple this morning.",
    "send_whatsapp_message": {"sid": "SMout"},
    "evaluate_response": INSIGHT,
    "translate_to_english": "translated english text",
    "extract_memorable_content": [
        {"content": "Loves gardening", "category": "hobby"},
        {"content": "Has grandchildren", "category": "family"},
    ],
    "store_memory": {"id": "mem-1"},
    "generate_recommendation": {"recommendation_text": "Ask about the roses.", "reason": "High engagement"},
    "check_consecutive_negative": False,
    "trigger_escalation_alert": {
        "elder_id": "elder-1",
        "caregiver_user_id": "user-1",
        "alert_type": "consecutive_low_engagement",
        "severity": "advisory",
        "message": "Arthur has been quieter than usual for a few days.",
        "requires_delivery": True,
    },
    "get_weather_summary": "normal",
}


@contextlib.contextmanager
def pipeline(**overrides):
    """Patches every dependency of the inbound task; yields a namespace of mocks."""
    specs = {**DEFAULTS, **overrides}
    mocks = {}
    with contextlib.ExitStack() as stack:
        for name, value in specs.items():
            kwargs = {"side_effect": value.value} if isinstance(value, Effect) else {"return_value": value}
            mocks[name] = stack.enter_context(patch(f"{MODULE}.{name}", **kwargs))
        yield types.SimpleNamespace(**mocks)


# --------------------------------------------------------------------------
# Guard rails: duplicates, unknown senders, nothing to work with
# --------------------------------------------------------------------------

def test_duplicate_message_sid_short_circuits():
    """Twilio retries webhooks; the same SID must never be processed twice."""
    with pipeline(get_interaction_by_twilio_sid={"id": "interaction-9"}) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["status"] == "duplicate"
    assert result["message_sid"] == "SM123"
    m.get_elder_by_whatsapp_number.assert_not_called()
    m.evaluate_response.assert_not_called()


def test_unknown_sender_is_ignored():
    with pipeline(get_elder_by_whatsapp_number=None) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["status"] == "unknown_sender"
    m.update_daily_interaction.assert_not_called()
    m.evaluate_response.assert_not_called()


def test_empty_text_body_is_dropped_without_a_reply():
    """An empty text body isn't worth a nudge — silence is better than noise."""
    payload = {**TEXT_PAYLOAD, "Body": "   "}
    with pipeline() as m:
        result = process_inbound_message(payload)

    assert result["status"] == "empty_transcript"
    assert result["source"] == "text"
    m.send_whatsapp_message.assert_not_called()


def test_no_open_interaction_does_not_fabricate_a_row():
    with pipeline(get_open_interaction_for_elder=None) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["status"] == "no_open_interaction"
    m.update_daily_interaction.assert_not_called()
    m.insert_interaction_insight.assert_not_called()


# --------------------------------------------------------------------------
# Transcript resolution
# --------------------------------------------------------------------------

def test_text_message_runs_the_full_pipeline():
    with pipeline() as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["status"] == "processed"
    assert result["source"] == "text"
    assert result["elder_id"] == "elder-1"
    assert result["interaction_id"] == "interaction-1"
    assert result["engagement_level"] == "high"
    assert result["sentiment_label"] == "positive"
    assert result["memories_stored"] == 2
    assert result["recommendation_created"] is True
    assert result["escalated"] is False

    # No media, so nothing should have been downloaded or transcribed.
    m.download_media.assert_not_called()
    m.transcribe_audio.assert_not_called()


def test_voice_note_is_downloaded_and_transcribed():
    with pipeline() as m:
        result = process_inbound_message(VOICE_PAYLOAD)

    assert result["status"] == "processed"
    assert result["source"] == "voice"
    m.download_media.assert_called_once_with("https://api.twilio.com/media/ME1")
    # Whisper gets the elder's language as a decoding hint.
    assert m.transcribe_audio.call_args.kwargs["language"] == "en"


def test_untranscribable_voice_note_asks_the_elder_to_resend():
    with pipeline(transcribe_audio=None) as m:
        result = process_inbound_message(VOICE_PAYLOAD)

    assert result["status"] == "empty_transcript"
    assert result["source"] == "voice"
    m.send_whatsapp_message.assert_called_once_with(VOICE_PAYLOAD["From"], UNCLEAR_AUDIO_REPLY)


def test_failed_media_download_is_treated_as_unclear_audio():
    with pipeline(download_media=None) as m:
        result = process_inbound_message(VOICE_PAYLOAD)

    assert result["status"] == "empty_transcript"
    m.transcribe_audio.assert_not_called()
    m.send_whatsapp_message.assert_called_once_with(VOICE_PAYLOAD["From"], UNCLEAR_AUDIO_REPLY)


# --------------------------------------------------------------------------
# Persistence + translation
# --------------------------------------------------------------------------

def test_reply_is_attached_to_the_open_interaction():
    with pipeline() as m:
        process_inbound_message(TEXT_PAYLOAD)

    interaction_id, data = m.update_daily_interaction.call_args.args
    assert interaction_id == "interaction-1"
    assert data["raw_response"] == TEXT_PAYLOAD["Body"]
    assert data["transcript_source"] == "text"
    assert data["language"] == "en"
    assert data["twilio_message_sid"] == "SM123"


def test_non_english_reply_is_translated_before_analysis():
    """The original stays in raw_response; only the analysis text is translated."""
    hindi_elder = {**ELDER, "preferred_language": "hi"}
    with pipeline(get_elder_by_whatsapp_number=hindi_elder) as m:
        process_inbound_message(TEXT_PAYLOAD)

    m.translate_to_english.assert_called_once_with(TEXT_PAYLOAD["Body"], "Hindi")
    m.evaluate_response.assert_called_once_with("translated english text")
    # Raw response must preserve the elder's own words.
    _, data = m.update_daily_interaction.call_args.args
    assert data["raw_response"] == TEXT_PAYLOAD["Body"]


def test_english_reply_skips_translation():
    with pipeline() as m:
        process_inbound_message(TEXT_PAYLOAD)

    m.translate_to_english.assert_not_called()
    m.evaluate_response.assert_called_once_with(TEXT_PAYLOAD["Body"])


def test_translation_failure_falls_back_to_the_original_text():
    hindi_elder = {**ELDER, "preferred_language": "hi"}
    with pipeline(
        get_elder_by_whatsapp_number=hindi_elder,
        translate_to_english=Effect(RuntimeError("translation offline")),
    ) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["status"] == "processed"
    m.evaluate_response.assert_called_once_with(TEXT_PAYLOAD["Body"])


def test_insight_is_persisted_with_the_full_evaluator_contract():
    with pipeline() as m:
        process_inbound_message(TEXT_PAYLOAD)

    record = m.insert_interaction_insight.call_args.args[0]
    assert record["interaction_id"] == "interaction-1"
    for key in (
        "sentiment_label", "sentiment_score", "engagement_level",
        "engagement_score", "response_depth", "topics", "safety_flag",
    ):
        assert record[key] == INSIGHT[key], key


def test_safety_flag_is_persisted_and_not_only_acted_on():
    """
    The flag must reach the database, not just the escalation branch — the caregiver
    dashboard reads it from interaction_insights.
    """
    flagged = {**INSIGHT, "safety_flag": True}
    with pipeline(evaluate_response=flagged) as m:
        process_inbound_message(TEXT_PAYLOAD)

    record = m.insert_interaction_insight.call_args.args[0]
    assert record["safety_flag"] is True


def test_insight_persist_failure_is_retried():
    """The elder's answer is already saved, so a retry re-analyzes rather than losing it."""
    with pipeline(insert_interaction_insight=Effect(RuntimeError("db down"))) as m:
        with pytest.raises(Exception):
            process_inbound_message(TEXT_PAYLOAD)

    # The reply was persisted before the failure.
    m.update_daily_interaction.assert_called_once()
    m.store_memory.assert_not_called()


# --------------------------------------------------------------------------
# Graceful degradation
# --------------------------------------------------------------------------

def test_memory_extraction_failure_does_not_break_the_pipeline():
    with pipeline(extract_memorable_content=Effect(RuntimeError("llm offline"))) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["status"] == "processed"
    assert result["memories_stored"] == 0
    m.store_memory.assert_not_called()


def test_one_failed_memory_does_not_discard_the_others():
    with pipeline(store_memory=Effect([RuntimeError("embedding failed"), {"id": "mem-2"}])) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["memories_stored"] == 1
    assert m.store_memory.call_count == 2


def test_incomplete_memories_are_skipped():
    with pipeline(extract_memorable_content=[{"content": "Loves gardening"}, {"category": "family"}]) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["memories_stored"] == 0
    m.store_memory.assert_not_called()


def test_recommendation_failure_still_keeps_the_insight():
    with pipeline(generate_recommendation=Effect(RuntimeError("llm offline"))) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["status"] == "processed"
    assert result["recommendation_created"] is False
    m.insert_interaction_insight.assert_called_once()
    m.insert_recommendation.assert_not_called()


def test_recommendation_is_stored_as_pending():
    with pipeline() as m:
        process_inbound_message(TEXT_PAYLOAD)

    record = m.insert_recommendation.call_args.args[0]
    assert record["status"] == "pending"
    assert record["elder_id"] == "elder-1"
    assert record["interaction_id"] == "interaction-1"
    assert record["recommendation_text"] == "Ask about the roses."


def test_weather_is_only_looked_up_when_coordinates_exist():
    with pipeline() as m:
        process_inbound_message(TEXT_PAYLOAD)
    m.get_weather_summary.assert_not_called()

    located = {**ELDER, "personal_context": {"lat": 15.4, "lon": 73.8}}
    with pipeline(get_elder_by_whatsapp_number=located) as m:
        process_inbound_message(TEXT_PAYLOAD)
    m.get_weather_summary.assert_called_once_with(15.4, 73.8)


def test_weather_failure_degrades_to_normal():
    located = {**ELDER, "personal_context": {"lat": 15.4, "lon": 73.8}}
    with pipeline(
        get_elder_by_whatsapp_number=located,
        get_weather_summary=Effect(RuntimeError("api down")),
    ) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["status"] == "processed"
    assert m.generate_recommendation.call_args.kwargs["weather_summary"] == "normal"


# --------------------------------------------------------------------------
# Escalation
# --------------------------------------------------------------------------

def test_safety_flag_escalates_immediately():
    flagged = {**INSIGHT, "safety_flag": True}
    with pipeline(evaluate_response=flagged, check_consecutive_negative=False) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["escalated"] is True
    m.trigger_escalation_alert.assert_called_once_with("elder-1")


def test_sustained_low_engagement_escalates():
    with pipeline(check_consecutive_negative=True) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["escalated"] is True
    m.trigger_escalation_alert.assert_called_once_with("elder-1")


def test_no_escalation_on_a_healthy_response():
    with pipeline() as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["escalated"] is False
    m.trigger_escalation_alert.assert_not_called()


def test_alert_is_delivered_when_a_caregiver_number_is_on_file():
    with_number = {**ELDER, "personal_context": {"caregiver_whatsapp": "+919000000009"}}
    with pipeline(get_elder_by_whatsapp_number=with_number, check_consecutive_negative=True) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["escalated"] is True
    m.send_whatsapp_message.assert_called_once_with(
        "+919000000009", DEFAULTS["trigger_escalation_alert"]["message"]
    )


def test_missing_caregiver_number_still_records_the_escalation():
    """The schema has no caregiver phone column yet — the dashboard is the fallback."""
    with pipeline(check_consecutive_negative=True) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["escalated"] is True
    m.send_whatsapp_message.assert_not_called()


def test_escalation_failure_does_not_fail_the_message():
    with pipeline(check_consecutive_negative=Effect(RuntimeError("db down"))) as m:
        result = process_inbound_message(TEXT_PAYLOAD)

    assert result["status"] == "processed"
    assert result["escalated"] is False
