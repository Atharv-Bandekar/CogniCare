import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Initialize Supabase Client
url: str = os.getenv("SUPABASE_URL")
key: str = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(url, key)

# Hardcoded demo user ID matching the one we inserted via SQL
DEMO_USER_ID = "d0d99042-3a31-482f-87d4-839f8d169d01"

def init_db():
    """
    In the cloud model, schemas are managed in the Supabase dashboard.
    We just use this to verify the connection.
    """
    try:
        # Simple ping to ensure credentials work
        supabase.table("users").select("id").limit(1).execute()
        print("✅ Successfully connected to Supabase PostgreSQL!")
    except Exception as e:
        print(f"❌ Database connection failed: {e}")

def get_demo_user_id() -> str:
    return DEMO_USER_ID

def log_conversation(user_id: str, question: str, response: str) -> str:
    """Logs the raw question and response, returning the new conversation ID."""
    data = {
        "user_id": user_id,
        "question": question,
        "response": response
    }
    result = supabase.table("conversations").insert(data).execute()
    return result.data[0]["id"]

def log_insight(conversation_id: str, sentiment_label: str, sentiment_score: float, 
                engagement_level: str, engagement_score: float, recommended_activity: str):
    """Logs the analysis from Agents 2 and 3."""
    # Convert activity to string if it's a dict
    activity_str = str(recommended_activity) if isinstance(recommended_activity, dict) else recommended_activity
    
    data = {
        "conversation_id": conversation_id,
        "sentiment_label": sentiment_label,
        "sentiment_score": float(sentiment_score),
        "engagement_level": engagement_level,
        "engagement_score": float(engagement_score),
        "recommended_activity": activity_str
    }
    supabase.table("insights").insert(data).execute()

def fetch_history(user_id: str = DEMO_USER_ID) -> list:
    """
    Fetches the joined history of conversations and insights for the Caregiver Dashboard.
    """
    # Supabase allows joining tables using the foreign key relationship
    response = supabase.table("conversations") \
        .select("timestamp, question, response, insights(sentiment_label, engagement_level, recommended_activity)") \
        .eq("user_id", user_id) \
        .order("timestamp", desc=True) \
        .execute()
    
    # Flatten the data to match the UI's expected dictionary format
    formatted_history = []
    for row in response.data:
        insight = row.get("insights", [{}])[0] if row.get("insights") else {}
        formatted_history.append({
            "timestamp": row["timestamp"],
            "question": row["question"],
            "response": row["response"],
            "sentiment_label": insight.get("sentiment_label"),
            "engagement_level": insight.get("engagement_level"),
            "recommended_activity": insight.get("recommended_activity")
        })
    return formatted_history