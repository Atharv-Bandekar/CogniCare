"""
Speech-to-text for inbound WhatsApp voice notes, via the Groq Whisper endpoint.

Elders often find speaking easier than typing, so voice notes are a first-class
input path — this module turns the downloaded audio into a transcript the
Evaluator and memory extraction can work with.

Env vars:
    GROQ_API_KEY
    GROQ_WHISPER_MODEL  (optional, defaults to whisper-large-v3-turbo)
"""
import os
import logging

import requests

logger = logging.getLogger(__name__)

GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_WHISPER_MODEL = "whisper-large-v3-turbo"
REQUEST_TIMEOUT = 60

# Maps the elder profile's preferred_language code to an ISO-639-1 hint for Whisper.
# Providing the hint measurably improves accuracy for Indic languages.
LANGUAGE_HINTS = {
    "en": "en",
    "hi": "hi",
    "mr": "mr",
    "ta": "ta",
}


def transcribe_audio(audio_bytes: bytes, language: str | None = None, filename: str = "voice.ogg") -> str | None:
    """
    Transcribes audio bytes to text using Groq's hosted Whisper.

    Args:
        audio_bytes (bytes): Raw audio (WhatsApp voice notes arrive as OGG/Opus).
        language (str | None): Elder's preferred language code ('en','hi','mr','ta').
        filename (str): Filename hint for the multipart upload; drives format detection.

    Returns:
        str | None: The transcript, or None if transcription failed or was empty.

    WHY: Returns None rather than raising so the inbound worker can fall back to
    a gentle "we couldn't hear that" reply instead of losing the interaction.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.error("GROQ_API_KEY missing; cannot transcribe audio.")
        return None
    if not audio_bytes:
        logger.warning("No audio bytes supplied to transcribe_audio.")
        return None

    model = os.getenv("GROQ_WHISPER_MODEL", DEFAULT_WHISPER_MODEL)
    data = {"model": model, "response_format": "json"}

    hint = LANGUAGE_HINTS.get((language or "").lower())
    if hint:
        data["language"] = hint

    try:
        response = requests.post(
            GROQ_TRANSCRIPTION_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            files={"file": (filename, audio_bytes)},
            data=data,
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        transcript = (response.json() or {}).get("text", "")
        transcript = transcript.strip()

        if not transcript:
            logger.warning("Whisper returned an empty transcript.")
            return None

        logger.info("Transcribed %d bytes of audio into %d characters.", len(audio_bytes), len(transcript))
        return transcript

    except Exception as exc:
        logger.error("Whisper transcription failed: %s", exc)
        return None
