"""
Database interaction layer for CogniCare V2.
Provides strict, typed CRUD operations for all Supabase tables.
Raises exceptions on failure to ensure the FastAPI layer handles errors properly.
"""

import os
from datetime import datetime, timedelta
from supabase import create_client, Client

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") # Use service role for backend admin tasks
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ==========================================
# ELDER PROFILES
# ==========================================

def insert_elder_profile(data: dict) -> dict:
    """Creates a new elder profile and links it to a caregiver."""
    response = supabase.table('elder_profiles').insert(data).execute()
    return response.data[0]

def get_elder_profile(elder_id: str) -> dict | None:
    """Fetches an elder profile by its UUID."""
    response = supabase.table('elder_profiles').select('*').eq('id', elder_id).execute()
    return response.data[0] if response.data else None

def update_elder_profile(elder_id: str, data: dict) -> dict:
    """Updates specific fields on an existing elder profile."""
    response = supabase.table('elder_profiles').update(data).eq('id', elder_id).execute()
    return response.data[0]


# ==========================================
# DAILY INTERACTIONS
# ==========================================

def insert_daily_interaction(data: dict) -> dict:
    """Records a new daily question and the elder's response."""
    response = supabase.table('daily_interactions').insert(data).execute()
    return response.data[0]

def get_interaction_by_twilio_sid(message_sid: str) -> dict | None:
    """Looks up an interaction by Twilio MessageSid. Used for Webhook idempotency."""
    response = supabase.table('daily_interactions').select('*').eq('twilio_message_sid', message_sid).execute()
    return response.data[0] if response.data else None

def get_interactions_by_elder(elder_id: str, limit: int = 20) -> list[dict]:
    """Fetches recent interaction history for a specific elder."""
    response = supabase.table('daily_interactions').select('*').eq('elder_id', elder_id).order('created_at', desc=True).limit(limit).execute()
    return response.data


# ==========================================
# INTERACTION INSIGHTS
# ==========================================

def insert_interaction_insight(data: dict) -> dict:
    """Saves the output from the Evaluator Agent (DeBERTa engagement/sentiment)."""
    response = supabase.table('interaction_insights').insert(data).execute()
    return response.data[0]

def get_recent_engagement_scores(elder_id: str, lookback_days: int = 3) -> list[float]:
    """
    Fetches the engagement scores over the last N days to calculate Dynamic Difficulty.
    Uses a table join via Supabase foreign keys.
    """
    cutoff_date = (datetime.utcnow() - timedelta(days=lookback_days)).isoformat()
    response = supabase.table('interaction_insights') \
        .select('engagement_score, daily_interactions!inner(elder_id, created_at)') \
        .eq('daily_interactions.elder_id', elder_id) \
        .gte('daily_interactions.created_at', cutoff_date) \
        .execute()
    
    return [record['engagement_score'] for record in response.data if record.get('engagement_score') is not None]


# ==========================================
# MEMORIES (pgvector RAG)
# ==========================================

def insert_memory(elder_id: str, content: str, category: str, embedding: list[float], source_interaction_id: str | None = None) -> dict:
    """Embeds and saves a new extracted memory into the vector database."""
    data = {
        "elder_id": elder_id,
        "content": content,
        "category": category,
        "embedding": embedding,
        "source_interaction_id": source_interaction_id
    }
    response = supabase.table('memories').insert(data).execute()
    return response.data[0]

def vector_search_memories(elder_id: str, query_embedding: list[float], top_k: int = 3) -> list[dict]:
    """
    Performs a cosine similarity search against elder memories.
    Requires an RPC function named 'match_memories' to be created in Supabase.
    """
    params = {
        "query_embedding": query_embedding,
        "target_elder_id": elder_id,
        "match_threshold": 0.7, # Adjustable confidence threshold
        "match_count": top_k
    }
    response = supabase.rpc('match_memories', params).execute()
    return response.data

def get_memories_by_elder(elder_id: str, limit: int = 50) -> list[dict]:
    """Fetches a standard chronological list of memories without vector search."""
    response = supabase.table('memories').select('*').eq('elder_id', elder_id).order('created_at', desc=True).limit(limit).execute()
    return response.data


# ==========================================
# RECOMMENDATIONS
# ==========================================

def insert_recommendation(data: dict) -> dict:
    """Saves a new Coordinator Agent generated family recommendation."""
    response = supabase.table('recommendations').insert(data).execute()
    return response.data[0]

def update_recommendation_status(recommendation_id: str, status: str) -> dict:
    """Updates recommendation status (e.g., 'pending' to 'done' or 'timed_out')."""
    data = {
        "status": status,
        "resolved_at": datetime.utcnow().isoformat() if status in ['done', 'dismissed'] else None
    }
    response = supabase.table('recommendations').update(data).eq('id', recommendation_id).execute()
    return response.data[0]

def get_recommendations_by_elder(elder_id: str, status: str | None = None) -> list[dict]:
    """Fetches recommendations, optionally filtered by status."""
    query = supabase.table('recommendations').select('*').eq('elder_id', elder_id)
    if status:
        query = query.eq('status', status)
    response = query.order('created_at', desc=True).execute()
    return response.data

def get_pending_recommendations_older_than(hours: int) -> list[dict]:
    """Used by the 12-hour fallback Celery task to find timed-out recommendations."""
    cutoff_time = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
    response = supabase.table('recommendations').select('*').eq('status', 'pending').lte('created_at', cutoff_time).execute()
    return response.data


# ==========================================
# FAMILY INTERACTIONS (Retention Loop)
# ==========================================

def insert_family_interaction(data: dict) -> dict:
    """Logs the caregiver's response (done/dismiss/custom) to a recommendation."""
    response = supabase.table('family_interactions').insert(data).execute()
    return response.data[0]

def get_unincorporated_family_suggestion(elder_id: str) -> dict | None:
    """
    Finds a custom caregiver suggestion that hasn't been woven into a daily question yet.
    Joins with recommendations table to filter by elder.
    """
    response = supabase.table('family_interactions') \
        .select('*, recommendations!inner(elder_id)') \
        .eq('recommendations.elder_id', elder_id) \
        .not_is('caregiver_suggestion', 'null') \
        .is_('incorporated_into_interaction_id', 'null') \
        .order('created_at', desc=False) \
        .limit(1) \
        .execute()
    return response.data[0] if response.data else None

def mark_family_suggestion_incorporated(family_interaction_id: str, interaction_id: str) -> dict:
    """Marks a family suggestion as successfully used by the Dynamic Question Engine."""
    response = supabase.table('family_interactions').update({'incorporated_into_interaction_id': interaction_id}).eq('id', family_interaction_id).execute()
    return response.data[0]


# ==========================================
# WEEKLY REPORTS
# ==========================================

def insert_weekly_report(data: dict) -> dict:
    """Saves the aggregated 7-day report for the caregiver dashboard."""
    response = supabase.table('weekly_reports').insert(data).execute()
    return response.data[0]

def get_latest_weekly_report(elder_id: str) -> dict | None:
    """Fetches the most recent weekly report for an elder."""
    response = supabase.table('weekly_reports').select('*').eq('elder_id', elder_id).order('cycle_end', desc=True).limit(1).execute()
    return response.data[0] if response.data else None


