"""
Twilio Webhook handlers.
These routes must execute in milliseconds and delegate all AI processing to Celery.
"""
import os
import logging

from fastapi import APIRouter, Request, Form, Header
from fastapi.responses import Response

from backend.celery_app.tasks.inbound import process_inbound_message
from backend.integrations.twilio_client import validate_twilio_signature

router = APIRouter()
logger = logging.getLogger(__name__)

# Empty TwiML: we reply asynchronously from the worker, not in the HTTP response.
EMPTY_TWIML = "<Response></Response>"

# WHY opt-out rather than opt-in: signature checking should be on by default in
# production. Set TWILIO_VALIDATE_SIGNATURE=false for local tunnel testing where
# the public URL Twilio signed doesn't match what the app sees.
def _signature_validation_enabled() -> bool:
    return os.getenv("TWILIO_VALIDATE_SIGNATURE", "true").strip().lower() not in ("false", "0", "no")


@router.post("/twilio/inbound")
async def twilio_inbound(
    request: Request,
    From: str = Form(...),
    Body: str = Form(""),
    MediaUrl0: str = Form(None),
    MessageSid: str = Form(...),
    x_twilio_signature: str = Header(None, alias="X-Twilio-Signature"),
):
    """
    Receives inbound WhatsApp messages.
    Immediately delegates to Celery to prevent blocking the FastAPI event loop.
    """
    # 1. Authenticity: only process webhooks Twilio actually signed.
    if _signature_validation_enabled():
        form_data = await request.form()
        params = {key: str(value) for key, value in form_data.items()}
        public_url = os.getenv("TWILIO_WEBHOOK_URL") or str(request.url)
        if not validate_twilio_signature(public_url, params, x_twilio_signature or ""):
            logger.warning("Rejected inbound webhook with an invalid Twilio signature.")
            # 403 tells Twilio not to keep retrying a request we'll never accept.
            return Response(content=EMPTY_TWIML, media_type="application/xml", status_code=403)

    payload = {
        "From": From,
        "Body": Body,
        "MediaUrl0": MediaUrl0,
        "MessageSid": MessageSid
    }

    # Fire and forget: send to Celery 'inbound' queue.
    # NOTE: MessageSid idempotency is enforced inside the worker (which owns the DB
    # session), keeping this handler free of blocking database I/O.
    process_inbound_message.apply_async(args=[payload], queue="inbound")

    # Return empty TwiML immediately (<5s timeout required by Twilio)
    return Response(content=EMPTY_TWIML, media_type="application/xml")

@router.post("/twilio/status")
async def twilio_status(request: Request):
    """Logs delivery status updates from Twilio (sent, delivered, read)."""
    form_data = await request.form()
    logger.info(f"Twilio Status Update: {form_data.get('MessageSid')} -> {form_data.get('MessageStatus')}")
    return Response(status_code=200)
