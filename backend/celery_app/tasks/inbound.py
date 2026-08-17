"""
Background tasks for processing inbound WhatsApp messages.
"""
from backend.celery_app import celery_app

@celery_app.task(bind=True, name="backend.celery_app.tasks.inbound.process_inbound_message")
def process_inbound_message(self, payload: dict):
    """
    TODO (Phase 2): Core async worker task.
    Will download media, run Whisper STT, evaluate sentiment, 
    extract memories, and generate caregiver recommendations.
    """
    print(f"Received Twilio Payload for background processing: MessageSid={payload.get('MessageSid')}")
    return True