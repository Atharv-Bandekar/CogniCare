import os
import json
from supabase import create_client, Client

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def init_db():
    print("Cloud database (Supabase) connected.")

def log_conversation(user_id: str, question: str, response: str) -> str:
    """Logs a new conversation tied to the secure user_id and returns the generated row ID."""
    data = {
        "user_id": user_id,
        "question": question,
        "response": response
    }
    result = supabase.table("conversations").insert(data).execute()
    return result.data[0]["id"]

def log_insight(conversation_id: str, sentiment_label: str, sentiment_score: float, engagement_level: str, engagement_score: float, activity_plan):
    """Logs the AI insights tied to the specific conversation_id."""
    
    # Your DB schema expects TEXT, so we safely convert the dictionary to a JSON string
    if isinstance(activity_plan, dict):
        activity_str = json.dumps(activity_plan)
    else:
        activity_str = str(activity_plan)

    data = {
        "conversation_id": conversation_id,
        "sentiment_label": sentiment_label,
        "sentiment_score": sentiment_score,
        "engagement_level": engagement_level,
        "engagement_score": engagement_score,
        "recommended_activity": activity_str  # <-- MATCHES YOUR SCHEMA EXACTLY!
    }
    supabase.table("insights").insert(data).execute()

def fetch_history(user_id: str) -> list:
    """Fetches the combined conversation and insights history for a specific user."""
    response = supabase.table("conversations") \
        .select("*, insights(*)") \
        .eq("user_id", user_id) \
        .order("timestamp", desc=True) \
        .execute()
    
    formatted_history = []
    for conv in response.data:
        insight = conv.get("insights", [{}])[0] if conv.get("insights") else {}
        
        # Safely parse the text string back into a dictionary for the frontend
        raw_activity = insight.get("recommended_activity", None)
        try:
            parsed_activity = json.loads(raw_activity) if raw_activity else None
        except (TypeError, ValueError):
            parsed_activity = raw_activity
        
        formatted_history.append({
            "timestamp": conv.get("timestamp"),
            "question": conv.get("question"),
            "response": conv.get("response"),
            "sentiment_label": insight.get("sentiment_label", "Pending"),
            "engagement_level": insight.get("engagement_level", "Pending"),
            "activity_plan": parsed_activity # <-- FRONTEND EXPECTS THIS NAME
        })
        
    return formatted_history