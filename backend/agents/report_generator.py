import os
import json
import logging
from typing import List, Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)

# WHY: Module-level instantiation reuses the connection pool across Celery background tasks.
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_weekly_summary(
    elder_profile: Dict[str, Any], 
    weekly_interactions: List[Dict[str, Any]], 
    weekly_insights: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Analyzes 7 days of interactions and insights to generate a structured, non-clinical 
    summary for the caregiver dashboard.
    
    Args:
        elder_profile (Dict[str, Any]): Demographics and context for the elder.
        weekly_interactions (List[Dict[str, Any]]): The raw interaction records for the week.
        weekly_insights (List[Dict[str, Any]]): The evaluator agent's metrics for those interactions.
        
    Returns:
        Dict[str, Any]: A structured summary containing trend text and recurring topics.
    """
    # WHY: We pre-format the raw data into a clean text block so the LLM doesn't waste 
    # tokens parsing nested JSON lists, keeping the request fast and cheap.
    history_text = ""
    for interaction, insight in zip(weekly_interactions, weekly_insights):
        history_text += f"Date: {interaction.get('interaction_date')}\n"
        history_text += f"Topic Domain: {interaction.get('domain')}\n"
        history_text += f"Engagement Level: {insight.get('engagement_level')}\n"
        history_text += f"Topics Extracted: {', '.join(insight.get('topics', []))}\n"
        history_text += f"Safety Flag Triggered: {insight.get('safety_flag', False)}\n\n"

    # WHY: Guardrails are hardcoded into the system prompt. This enforces our strict 
    # rule against providing medical or diagnostic assessments to the caregiver.
    system_prompt = f"""
    You are an AI wellness analyst generating a weekly summary for a caregiver about an elderly user named {elder_profile.get('name', 'the user')}.
    
    STRICT RULES:
    1. NEVER diagnose, assess, or use clinical terminology (e.g., DO NOT USE words like "dementia", "cognitive decline", "Alzheimer's", "depression").
    2. Focus strictly on mood, social engagement, and recurring conversation themes. Keep the tone supportive.
    3. Output MUST be valid JSON matching this exact schema:
    {{
        "engagement_trend": "A brief 1-2 sentence summary of their participation levels.",
        "emotional_trend": "A brief 1-2 sentence summary of their sentiment and mood.",
        "recurring_topics": ["List", "of", "short", "strings", "representing", "topics discussed"]
    }}
    """

    try:
        # WHY: Llama-3 8B with JSON mode is highly reliable for extracting structured summaries.
        # Temperature is set low (0.2) to prevent hallucinatory narrative drifting.
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Here is the weekly data:\n{history_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        
        raw_output = response.choices[0].message.content
        parsed_report = json.loads(raw_output)
        
        return parsed_report
        
    except Exception as e:
        logger.error(f"Failed to generate weekly report via Groq: {e}")
        # WHY: Provide a safe, schema-compliant fallback so the UI never crashes on an API failure.
        return {
            "engagement_trend": "Insufficient data to determine a trend this week.",
            "emotional_trend": "Insufficient data to determine a trend this week.",
            "recurring_topics": []
        }