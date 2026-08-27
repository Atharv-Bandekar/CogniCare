"""
Weekly reports endpoints for the caregiver dashboard.
"""
from fastapi import APIRouter, HTTPException
from typing import Optional
import backend.database.db as db

router = APIRouter()

@router.get("/{elder_id}/weekly-reports")
def get_weekly_reports(elder_id: str, limit: int = 10):
    """Fetches all weekly reports for an elder (paginated)."""
    try:
        response = db.supabase.table('weekly_reports').select('*').eq('elder_id', elder_id).order('cycle_end', desc=True).limit(limit).execute()
        return response.data or []
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{elder_id}/weekly-reports/latest")
def get_latest_weekly_report(elder_id: str):
    """Fetches the most recent weekly report for an elder."""
    try:
        report = db.get_latest_weekly_report(elder_id)
        if not report:
            raise HTTPException(status_code=404, detail="No weekly report found")
        return report
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))