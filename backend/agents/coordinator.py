"""
Coordinator Agent responsible for generating safe, actionable family recommendations.
Enforces strict guardrails for proximity, mobility constraints, and clinical language.
"""
import os
import json
import logging
from groq import Groq

logger = logging.getLogger(__name__)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Diagnostic words the AI is strictly forbidden from outputting
FORBIDDEN_WORDS = ["dementia", "depression", "alzheimer", "cognitive impairment", "diagnose", "clinical"]

def generate_recommendation(elder: dict, evaluator_output: dict, domain: str, memories: list, weather_summary: str) -> dict:
    """
    Calls Groq Llama-3 to generate a family recommendation based on today's interaction.
    Applies hardcoded keyword safety filters before returning the result.
    """
    proximity = elder.get("proximity", "remote")
    mobility = elder.get("mobility_constraints", [])
    
    system_prompt = f"""
    You are generating ONE practical family recommendation based on today's elder interaction.

    Inputs:
    - Evaluator output: Engagement: {evaluator_output.get('engagement_level')}, Sentiment: {evaluator_output.get('sentiment_label')}, Topics: {evaluator_output.get('topics')}, Safety Flag: {evaluator_output.get('safety_flag')}
    - Today's domain: {domain}
    - Retrieved memories: {memories}
    - Caregiver proximity: {proximity}  [remote | live_in | nearby]
    - Mobility constraints: {mobility}
    - Local weather: {weather_summary}

    STRICT RULES:
    1. Proximity governs recommendation TYPE:
       - remote → phone/video call, voice message, photo sharing only. NEVER suggest in-person activity.
       - live_in → in-person activities during natural moments (dinner, walk together, shared task).
       - nearby → either remote or short in-person visit suggestions.
    2. Mobility is a HARD CONSTRAINT: if mobility_constraints includes "seated_only" or "limited_outdoor",
       NEVER suggest walking, standing, or outdoor physical activity. Suggest seated/indoor alternatives.
    3. Weather guardrail: if weather indicates heavy rain or extreme heat AND recommendation is outdoor,
       pivot to an indoor equivalent.
    4. If safety_flag is true, the recommendation MUST include a gentle suggestion for the caregiver
       to consider checking in more closely or consulting a professional — using non-clinical language.
       NEVER use the words "dementia," "depression," "Alzheimer's," "cognitive impairment," "diagnose."
    5. Output strictly in JSON format: {{ "recommendation_text": "...", "reason": "..." }}
    """

    try:
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[{"role": "system", "content": system_prompt}],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        
        result_text = response.choices[0].message.content
        result_json = json.loads(result_text)
        
        rec_text_lower = result_json.get("recommendation_text", "").lower()

        # GUARDRAIL 1: Diagnostic language filter
        if any(word in rec_text_lower for word in FORBIDDEN_WORDS):
            logger.warning("Agent attempted to output diagnostic language. Overriding.")
            return _fallback_recommendation()

        # GUARDRAIL 2: Remote proximity check
        if proximity == "remote" and any(word in rec_text_lower for word in ["walk together", "in person", "visit", "dinner"]):
            logger.warning("Agent suggested in-person activity for remote caregiver. Overriding.")
            return _fallback_recommendation()

        # GUARDRAIL 3: Mobility constraint check
        if any(c in mobility for c in ["seated_only", "limited_outdoor"]) and any(word in rec_text_lower for word in ["walk", "hike", "stand", "outside"]):
            logger.warning("Agent suggested restricted physical activity. Overriding.")
            return _fallback_recommendation()

        return result_json

    except Exception as e:
        logger.error(f"Coordinator generation failed: {e}")
        return _fallback_recommendation()

def _fallback_recommendation() -> dict:
    """Safe generic fallback if the AI fails or trips a safety guardrail."""
    return {
        "recommendation_text": "Give your loved one a quick phone call today to say hello and ask how their morning went.",
        "reason": "A simple check-in builds connection safely."
    }