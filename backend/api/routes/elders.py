"""
Elder Profile Onboarding & Management API.
"""
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

class ElderUpdate(BaseModel):
    preferred_language: Optional[str] = None
    preferred_interaction_time: Optional[str] = None
    timezone: Optional[str] = None
    proximity: Optional[str] = Field(None, pattern="^(remote|live_in|nearby)$")
    mobility_constraints: Optional[List[str]] = None
    personal_context: Optional[dict] = None

@router.post("/", status_code=201)
def create_elder(elder: ElderCreate):
    """Creates a new elder profile and links it to a caregiver."""
    try:
        new_elder = db.insert_elder_profile(elder.model_dump())
        return new_elder
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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