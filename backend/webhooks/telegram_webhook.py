"""
Telegram webhook handler.

Mirrors twilio_webhook.py: authenticate, enqueue to Celery, return immediately.
Telegram re-delivers an update if the webhook doesn't answer 200 quickly, so ALL
real work (LLM calls, DB writes) happens in the worker, never in this handler.

Security: setWebhook can register a secret_token; Telegram then sends it back in
the X-Telegram-Bot-Api-Secret-Token header on every update. We compare it to
TELEGRAM_WEBHOOK_SECRET. This is the Telegram analogue of Twilio's request
signature — simpler because it's a shared secret rather than an HMAC.
"""
import os
import logging

from fastapi import APIRouter, Request, Header
from fastapi.responses import JSONResponse

from backend.celery_app.tasks.telegram_bot import process_telegram_update

router = APIRouter()
logger = logging.getLogger(__name__)


# WHY opt-out rather than opt-in: the secret check should be on by default. Set
# TELEGRAM_VALIDATE_SECRET=false only for a first local smoke test where you
# haven't registered a secret_token yet.
def _secret_validation_enabled() -> bool:
    return os.getenv("TELEGRAM_VALIDATE_SECRET", "true").strip().lower() not in ("false", "0", "no")


@router.post("/telegram/inbound")
async def telegram_inbound(
    request: Request,
    x_telegram_secret: str = Header(None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    """Receives Telegram updates and hands them to the Celery inbound queue."""
    # 1. Authenticity: only process updates carrying our shared secret.
    if _secret_validation_enabled():
        expected = os.getenv("TELEGRAM_WEBHOOK_SECRET", "")
        if not expected or x_telegram_secret != expected:
            logger.warning("Rejected Telegram update with an invalid secret token.")
            return JSONResponse({"ok": False}, status_code=403)

    # 2. Parse. Malformed body -> ack anyway so Telegram doesn't retry forever.
    try:
        update = await request.json()
    except Exception:
        logger.warning("Received a Telegram update with an unparseable body.")
        return JSONResponse({"ok": True})

    # 3. Extract the message (handle plain and edited messages).
    message = update.get("message") or update.get("edited_message") or {}
    chat = message.get("chat") or {}
    sender = message.get("from") or {}
    voice = message.get("voice") or {}

    chat_id = chat.get("id")
    if chat_id is None:
        # Non-message update (callback query, my_chat_member, etc.) — ack + ignore.
        return JSONResponse({"ok": True})

    payload = {
        "chat_id": chat_id,
        "message_id": message.get("message_id"),
        "text": message.get("text"),
        "voice_file_id": voice.get("file_id"),
        "first_name": sender.get("first_name"),
    }

    # Fire and forget onto the same 'inbound' queue the worker already consumes.
    process_telegram_update.apply_async(args=[payload], queue="inbound")

    return JSONResponse({"ok": True})
