"""
Recommendation management endpoints for the caregiver dashboard.
Powers the family feedback loop (Done / Dismiss / Custom Suggestion).
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
import backend.database.db as db

router = APIRouter()

class SuggestionInput(BaseModel):
    suggestion_text: str
    caregiver_user_id: str

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
        # Perfectly organized: Catch the specific missing record error from db.py
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        # Fallback for all other database/system errors
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
    Also sets the recommendation status to 'done' per product rules.
    """
    try:
        db.update_recommendation_status(recommendation_id, "done")
        db.insert_family_interaction({
            "recommendation_id": recommendation_id,
            "caregiver_user_id": payload.caregiver_user_id,
            "reaction": "done",
            "caregiver_suggestion": payload.suggestion_text
        })
        return {"status": "success"}
    except ValueError as e:
        # Perfectly organized: matches your /done endpoint
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))