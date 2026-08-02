import json
import re
from .base import call_llm

def extract_json_safely(llm_response: str) -> dict:
    """Strips markdown and conversational text to cleanly parse JSON."""
    try:
        # Find everything between the first { and the last }
        match = re.search(r'\{.*\}', llm_response, re.DOTALL)
        if match:
            clean_text = match.group(0)
            return json.loads(clean_text)
        
        # Fallback if the regex somehow misses, try parsing the raw string
        return json.loads(llm_response)
        
    except json.JSONDecodeError as e:
        print(f"Failed to parse LLM output. Raw text was:\n{llm_response}")
        return None # Return None so the caller knows to use the fallback

class CoordinatorAgent:
    # 1. Update fallbacks to match the new JSON structure so the app doesn't crash if the API fails
    FALLBACK_ACTIVITIES = {
        "Positive": {
            "morning_activity": "Sit by a window with your morning tea and reflect on your favorite memories.",
            "afternoon_activity": "Look through an old photo album to find pictures related to your past.",
            "evening_activity": "Call a family member or speak to someone at dinner to share this exact memory with them.",
            "caregiver_rationale": "Leverages their positive, engaged mood to encourage active social sharing and nostalgia."
        },
        "Neutral": {
            "morning_activity": "Take a slow, 10-minute walk around the house or garden to get some fresh air.",
            "afternoon_activity": "Listen to a classic radio show or a favorite old song while resting.",
            "evening_activity": "Ask a younger family member to show you photos of their day.",
            "caregiver_rationale": "Provides gentle, low-strain stimulation to maintain baseline cognitive engagement."
        },
        "Negative": {
            "morning_activity": "Sit somewhere sunny and comfortable with a warm drink for 10 minutes.",
            "afternoon_activity": "Do a very light stretching exercise or deep breathing for 5 minutes.",
            "evening_activity": "Have a quiet dinner with the family, focusing just on being present rather than talking heavily.",
            "caregiver_rationale": "Prioritizes emotional comfort and rest over high cognitive demand."
        }
    }

    def generate_activity(self, user_text, evaluation, language="English"):
        # 2. Inject the new JSON-forcing System Prompt
        system_prompt = (
            "You are an expert Geriatric Cognitive Engagement Specialist. Your task is to generate a personalized, "
            "3-part daily activity plan for an elderly user (80+ years old) living in a multi-generational household.\n"
            "INSTRUCTIONS:\n"
            "1. Do NOT suggest quick, one-off tasks.\n"
            "2. Create a structured plan broken into Morning, Afternoon, and Evening micro-activities.\n"
            "3. Morning: Focus on gentle Sensory or light Physical engagement.\n"
            "4. Afternoon: Focus on Cognitive or Creative engagement.\n"
            "5. Evening: MUST focus on Social engagement (e.g., sharing a story with younger family members).\n"
            "6. Keep activities low-strain, screen-free, and themed around the user's memory.\n"
            f"7. CRITICAL: Output MUST be in {language} language.\n"
            "OUTPUT FORMAT:\n"
            "Return ONLY a valid JSON object with the exact keys: 'morning_activity', 'afternoon_activity', 'evening_activity', 'caregiver_rationale'. "
            "Do not include markdown or conversational filler."
        )
        
        # 3. Pass the DeBERTa-v3 sentiment state and user text directly into the prompt
        user_prompt = (
            f"User's conversational memory/topic: \"{user_text}\"\n"
            f"User's current emotional state/mood: {evaluation['sentiment_label']} (score {evaluation['sentiment_score']})\n"
            f"User's engagement level: {evaluation['engagement_level']}\n\n"
            "Generate the JSON daily plan."
        )

        # 4. Increase max_tokens because a JSON object takes more words than a single sentence
        result = call_llm(system_prompt, user_prompt, max_tokens=1024)
        
        if result:
            # 5. Use the bulletproof regex extractor
            activity_plan = extract_json_safely(result)
            if activity_plan:
                return activity_plan

        # Return the structured fallback if the LLM fails, times out, or fails to parse
        return self.FALLBACK_ACTIVITIES.get(
            evaluation["sentiment_label"], self.FALLBACK_ACTIVITIES["Neutral"]
        )