"""
Telegram Bot API integration — the recruiter-facing demo channel.

WHY Telegram (and not just WhatsApp): Twilio's WhatsApp *trial* sender is
template-only and requires pre-registered test numbers, so a stranger who finds
the GitHub repo or the deployment can't actually use the app. A Telegram bot is
public by default — anyone with the t.me link taps "Start" and holds a live
conversation, for free, with no verification. That makes it the channel a
recruiter can genuinely try.

This module mirrors integrations/twilio_client.py on purpose: a thin `requests`
wrapper (no telegram SDK dependency), functions that NEVER raise — they return
dict|None so the Celery callers decide what's retryable — and it logs the API
response *body* on failure, because Telegram (like Twilio) hides the real reason
behind a bare HTTP status.

Env vars:
    TELEGRAM_BOT_TOKEN        from @BotFather, e.g. "123456:ABC-DEF..."
    TELEGRAM_WEBHOOK_URL      public https URL Telegram POSTs updates to
                              (…/webhooks/telegram/inbound)
    TELEGRAM_WEBHOOK_SECRET   optional shared secret; Telegram echoes it back in
                              the X-Telegram-Bot-Api-Secret-Token header
"""
import os
import logging

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"
REQUEST_TIMEOUT = 15


def _token() -> str | None:
    """Returns the bot token, or None if not configured."""
    return os.getenv("TELEGRAM_BOT_TOKEN")


def _method_url(method: str) -> str | None:
    """Builds the Bot API URL for a method, or None if the token is missing."""
    token = _token()
    return f"{API_BASE}/bot{token}/{method}" if token else None


def send_telegram_message(chat_id, text: str) -> dict | None:
    """
    Sends a text message to a Telegram chat.

    Args:
        chat_id: The target chat id (int or str) from the inbound update.
        text (str): The message body.

    Returns:
        dict | None: Telegram's JSON response (contains 'result'), or None on failure.

    WHY None instead of raising: mirrors send_whatsapp_message so the pipeline's
    send-failure handling is identical across channels.
    """
    if not _token():
        logger.error("TELEGRAM_BOT_TOKEN is not set; message not sent.")
        return None
    if not text or not text.strip():
        logger.warning("Refusing to send an empty Telegram message.")
        return None

    try:
        response = requests.post(
            _method_url("sendMessage"),
            json={"chat_id": chat_id, "text": text},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        logger.info("Telegram message sent to chat %s.", chat_id)
        return data
    except requests.HTTPError as exc:
        # Telegram returns {"ok":false,"error_code":...,"description":"..."} — the
        # description is the actual reason (e.g. "chat not found", "bot was blocked
        # by the user"), which the bare status code hides.
        body = exc.response.text if exc.response is not None else ""
        logger.error("Failed to send Telegram message: %s | Telegram response: %s", exc, body)
        return None
    except Exception as exc:
        logger.error("Failed to send Telegram message: %s", exc)
        return None


def send_chat_action(chat_id, action: str = "typing") -> None:
    """
    Best-effort 'typing…' indicator so the recruiter sees activity while the
    multi-step agent pipeline (LLM + evaluator + memory) runs. Never raises.
    """
    if not _token():
        return
    try:
        requests.post(
            _method_url("sendChatAction"),
            json={"chat_id": chat_id, "action": action},
            timeout=REQUEST_TIMEOUT,
        )
    except Exception as exc:
        logger.debug("sendChatAction failed (non-fatal): %s", exc)


def download_telegram_voice(file_id: str) -> bytes | None:
    """
    Downloads a Telegram voice note's bytes for Whisper transcription.

    Telegram is a two-step download: getFile resolves a temporary file_path, then
    the file is fetched from the /file/bot<token>/<path> endpoint. Voice notes
    arrive as OGG/Opus, which is exactly what integrations.stt.transcribe_audio
    expects (its default filename is 'voice.ogg').

    Returns:
        bytes | None: Raw audio, or None on any failure.
    """
    token = _token()
    if not token or not file_id:
        return None
    try:
        info = requests.get(
            _method_url("getFile"),
            params={"file_id": file_id},
            timeout=REQUEST_TIMEOUT,
        )
        info.raise_for_status()
        file_path = ((info.json() or {}).get("result") or {}).get("file_path")
        if not file_path:
            logger.warning("getFile returned no file_path for file_id %s.", file_id)
            return None

        download = requests.get(
            f"{API_BASE}/file/bot{token}/{file_path}",
            timeout=REQUEST_TIMEOUT,
        )
        download.raise_for_status()
        return download.content
    except Exception as exc:
        logger.error("Failed to download Telegram voice file: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Webhook management helpers.
#
# Telegram needs to be told, once, where to POST updates (setWebhook). Run these
# from the API container whenever your public tunnel URL changes, e.g.:
#
#   docker compose exec api python -c \
#     "from backend.integrations.telegram_client import set_webhook; print(set_webhook())"
#
# They read TELEGRAM_WEBHOOK_URL / TELEGRAM_WEBHOOK_SECRET from the environment.
# ---------------------------------------------------------------------------

def set_webhook(url: str | None = None, secret: str | None = None) -> dict | None:
    """Registers (or updates) the webhook URL with Telegram."""
    if not _token():
        logger.error("TELEGRAM_BOT_TOKEN is not set.")
        return None
    url = url or os.getenv("TELEGRAM_WEBHOOK_URL")
    secret = secret or os.getenv("TELEGRAM_WEBHOOK_SECRET")
    if not url:
        logger.error("No TELEGRAM_WEBHOOK_URL provided; cannot set webhook.")
        return None

    payload = {"url": url, "drop_pending_updates": True}
    # secret_token is echoed back by Telegram in every update's
    # X-Telegram-Bot-Api-Secret-Token header, which the webhook validates.
    if secret:
        payload["secret_token"] = secret

    try:
        response = requests.post(_method_url("setWebhook"), json=payload, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
        logger.info("Telegram setWebhook -> %s", data)
        return data
    except Exception as exc:
        logger.error("setWebhook failed: %s", exc)
        return None


def delete_webhook() -> dict | None:
    """Removes the webhook (e.g. to switch to long-polling for local debugging)."""
    if not _token():
        return None
    try:
        response = requests.post(
            _method_url("deleteWebhook"),
            json={"drop_pending_updates": True},
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.error("deleteWebhook failed: %s", exc)
        return None


def get_webhook_info() -> dict | None:
    """Returns Telegram's current webhook registration — handy for debugging."""
    if not _token():
        return None
    try:
        response = requests.get(_method_url("getWebhookInfo"), timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        return response.json()
    except Exception as exc:
        logger.error("getWebhookInfo failed: %s", exc)
        return None
