"""
Recommendation management endpoints for the caregiver dashboard.
Powers the family feedback loop (Done / Dismiss / Custom Suggestion).
"""
import logging

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import backend.database.db as db
from backend.integrations.telegram_client import send_telegram_message

logger = logging.getLogger(__name__)
router = APIRouter()

class SuggestionInput(BaseModel):
    suggestion_text: str
    caregiver_user_id: str


def _get_elder_id_from_recommendation(recommendation_id: str) -> str | None:
    """Look up the elder_id from a recommendation ID via Supabase."""
    try:
        response = db.supabase.table("recommendations").select("elder_id").eq("id", recommendation_id).execute()
        if response.data:
            return response.data[0].get("elder_id")
    except Exception as exc:
        logger.error("Failed to look up elder for recommendation %s: %s", recommendation_id, exc)
    return None


@router.get("/{elder_id}/recommendations")
def get_recommendations(elder_id: str, status: str = Query(None, description="Filter by status e.g., 'pending'")):
    """Fetches recommendations for an elder."""
    try:
        return db.get_recommendations_by_elder(elder_id, status)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/recommendations/{recommendation_id}/done")
def mark_recommendation_done(recommendation_id: str, caregiver_user_id: str):
    """Marks a recommendation as completed and logs the family interaction."""
    try:
        db.update_recommendation_status(recommendation_id, "done")
        db.insert_family_interaction({
            "recommendation_id": recommendation_id,
            "caregiver_user_id": caregiver_user_id,
            "reaction": "done"
        })
        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/recommendations/{recommendation_id}/dismiss")
def dismiss_recommendation(recommendation_id: str, caregiver_user_id: str):
    """Dismisses a recommendation."""
    try:
        db.update_recommendation_status(recommendation_id, "dismissed")
        db.insert_family_interaction({
            "recommendation_id": recommendation_id,
            "caregiver_user_id": caregiver_user_id,
            "reaction": "dismiss"
        })
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/recommendations/{recommendation_id}/suggest")
def submit_custom_suggestion(recommendation_id: str, payload: SuggestionInput):
    """
    Submits a custom caregiver suggestion.
    Sets the recommendation status to 'done' and sends the message to the elder via Telegram.
    """
    try:
        db.update_recommendation_status(recommendation_id, "done")
        db.insert_family_interaction({
            "recommendation_id": recommendation_id,
            "caregiver_user_id": payload.caregiver_user_id,
            "reaction": "done",
            "caregiver_suggestion": payload.suggestion_text
        })

        # Send the custom suggestion to the elder via Telegram
        try:
            elder_id = _get_elder_id_from_recommendation(recommendation_id)
            if elder_id:
                elder = db.get_elder_profile(elder_id)
                if elder:
                    chat_id = elder.get("telegram_user_id") or elder.get("telegram_chat_id")
                    if chat_id:
                        send_telegram_message(chat_id, f"Message from your caregiver:\n\n\"{payload.suggestion_text}\"")
                    else:
                        logger.warning("Cannot send suggestion: elder %s has no Telegram ID", elder_id)
        except Exception as send_exc:
            logger.error("Failed to send suggestion via Telegram: %s", send_exc)

        return {"status": "success"}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
