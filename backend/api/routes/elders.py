"""
Elder Profile Onboarding & Management API.

Supports both WhatsApp (legacy) and Telegram (production) channels.
"""
import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import backend.database.db as db

router = APIRouter()

# Pydantic models for strict request validation
class ElderCreate(BaseModel):
    caregiver_user_id: str
    name: str
    whatsapp_number: str
    preferred_language: str = "en"
    preferred_interaction_time: str
    timezone: str = "Asia/Kolkata"
    proximity: str = Field(..., pattern="^(remote|live_in|nearby)$")
    mobility_constraints: Optional[List[str]] = []
    personal_context: Optional[dict] = {}

class ElderCreateTelegram(BaseModel):
    """Create elder for Telegram production channel (no WhatsApp number required)."""
    caregiver_user_id: str
    name: str
    preferred_language: str = "en"
    preferred_interaction_time: str
    timezone: str = "Asia/Kolkata"
    proximity: str = Field(..., pattern="^(remote|live_in|nearby)$")
    mobility_constraints: Optional[List[str]] = []
    personal_context: Optional[dict] = {}

class ElderUpdate(BaseModel):
    preferred_language: Optional[str] = None
    preferred_interaction_time: Optional[str] = None
    timezone: Optional[str] = None
    proximity: Optional[str] = Field(None, pattern="^(remote|live_in|nearby)$")
    mobility_constraints: Optional[List[str]] = None
    personal_context: Optional[dict] = None

class DeepLinkResponse(BaseModel):
    """Response containing the Telegram deep-link for elder onboarding."""
    elder_id: str
    deep_link: str
    bot_username: str

@router.post("/", status_code=201)
def create_elder(elder: ElderCreate):
    """Creates a new elder profile for WhatsApp channel (legacy)."""
    try:
        new_elder = db.insert_elder_profile(elder.model_dump())
        return new_elder
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/telegram", status_code=201)
def create_elder_telegram(elder: ElderCreateTelegram):
    """Creates a new elder profile for Telegram production channel (no WhatsApp number)."""
    try:
        # Use synthetic whatsapp_number placeholder (NOT NULL UNIQUE in schema)
        data = elder.model_dump()
        data['whatsapp_number'] = f"tg:pending:{elder.name.lower().replace(' ', '_')}"
        new_elder = db.insert_elder_profile(data)
        return new_elder
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{elder_id}/deep-link", response_model=DeepLinkResponse)
def get_telegram_deep_link(elder_id: str):
    """
    Generates a Telegram deep-link for elder onboarding.

    Caregiver shares this link with the elder (via WhatsApp/SMS/email).
    Elder taps it → opens Telegram bot with start parameter → bot links their user_id to this elder.
    """
    elder = db.get_elder_profile(elder_id)
    if not elder:
        raise HTTPException(status_code=404, detail="Elder not found")

    bot_username = os.getenv("TELEGRAM_BOT_USERNAME", "CogniCareDemoBot")
    deep_link = f"https://t.me/{bot_username}?start=elder_{elder_id}"

    return DeepLinkResponse(
        elder_id=elder_id,
        deep_link=deep_link,
        bot_username=bot_username
    )

@router.get("/{elder_id}")
def get_elder(elder_id: str):
    """Fetches an elder profile by its UUID."""
    elder = db.get_elder_profile(elder_id)
    if not elder:
        raise HTTPException(status_code=404, detail="Elder not found")
    return elder

@router.get("/")
def list_elders():
    """Lists all elder profiles (for demo/debug)."""
    return db.get_all_elders() or []

@router.patch("/{elder_id}")
def update_elder(elder_id: str, updates: ElderUpdate):
    """Updates specific fields on an existing elder profile."""
    # Only update fields that were actually provided
    update_data = {k: v for k, v in updates.model_dump().items() if v is not None}
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided to update")

    try:
        updated_elder = db.update_elder_profile(elder_id, update_data)
        return updated_elder
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))