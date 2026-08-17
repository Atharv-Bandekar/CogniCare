"""
Twilio Webhook handlers. 
These routes must execute in milliseconds and delegate all AI processing to Celery.
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import Response
import logging

# Import the Celery task stub
from backend.celery_app.tasks.inbound import process_inbound_message

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/twilio/inbound")
async def twilio_inbound(
    request: Request,
    From: str = Form(...),
    Body: str = Form(""),
    MediaUrl0: str = Form(None),
    MessageSid: str = Form(...)
):
    """
    Receives inbound WhatsApp messages.
    Immediately delegates to Celery to prevent blocking the FastAPI event loop.
    """
    # TODO (Future): Implement Twilio X-Twilio-Signature validation for production security
    # TODO (Phase 2): Implement MessageSid idempotency check via database

    payload = {
        "From": From,
        "Body": Body,
        "MediaUrl0": MediaUrl0,
        "MessageSid": MessageSid
    }

    # Fire and forget: send to Celery 'inbound' queue
    process_inbound_message.apply_async(args=[payload], queue="inbound")

    # Return empty TwiML immediately (<5s timeout required by Twilio)
    return Response(content="<Response></Response>", media_type="application/xml")

@router.post("/twilio/status")
async def twilio_status(request: Request):
    """Logs delivery status updates from Twilio (sent, delivered, read)."""
    form_data = await request.form()
    logger.info(f"Twilio Status Update: {form_data.get('MessageSid')} -> {form_data.get('MessageStatus')}")
    return Response(status_code=200)