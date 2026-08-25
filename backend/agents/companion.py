"""
Companion Agent — generates the warm, user-facing reply to an elder's answer.

WHY this exists: the WhatsApp inbound pipeline (Phase 3B) analyses the elder's
reply (evaluate -> insight -> memory -> caregiver recommendation) but sends the
elder NOTHING back — the only outbound messages are the scheduled question and
the caregiver escalation. That's fine for a fire-and-forget WhatsApp cadence, but
a live Telegram conversation must feel answered. This agent produces that reply.

It deliberately reuses agents.base.call_llm and mirrors the Interviewer's
non-clinical guardrails: never acknowledge that anything is being measured.
"""
from .base import call_llm

# Used when the LLM is unavailable, so the conversation never stalls in silence.
FALLBACK_REPLY = "Thank you for sharing that with me — I really enjoyed hearing it."


def generate_companion_reply(
    elder_name: str,
    language: str,
    question: str,
    elder_answer: str,
) -> str:
    """
    Writes a short, warm acknowledgement of what the elder just shared.

    Args:
        elder_name (str): For light personalization.
        language (str): Target language name ("English", "Hindi", ...); reply is
            written ONLY in this language.
        question (str): The question the elder was answering (for context).
        elder_answer (str): The elder's reply, in their own words.

    Returns:
        str: The reply text (falls back to a gentle generic line if the LLM fails).

    Note: intentionally does NOT ask a new question — the telegram_bot task sends
    the next question separately, so the acknowledgement and the next prompt land
    as two natural, distinct messages.
    """
    system_prompt = f"""
    You are a warm, patient conversational companion for an elderly person named {elder_name}.
    A moment ago you gently asked: "{question}"
    They replied, in their own words: "{elder_answer}"

    Write a short, natural, spoken-style response that:
    - warmly acknowledges something SPECIFIC they said (never generic praise like "that's great"),
    - shows genuine, personal interest and a little warmth,
    - is 1-2 sentences, the way a caring family friend would speak.

    Hard rules:
    - Do NOT ask a new question (another message will do that).
    - Never mention testing, scoring, evaluation, memory exercises, "cognition",
      or anything clinical. You are a friend, not a survey.
    - Reply ONLY in {language}, in natural script (no Latin-letter English words
      mixed into Hindi/Marathi/Tamil unless it's a proper noun).
    - Output ONLY the reply text — no quotes, no preamble, no explanation.
    """
    user_prompt = "Write the reply."

    result = call_llm(system_prompt, user_prompt, max_tokens=120, temperature=0.7)
    if result:
        return result.strip().strip('"')
    return FALLBACK_REPLY
