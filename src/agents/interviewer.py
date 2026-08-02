import random
from .base import call_llm

class InterviewerAgent:
    FALLBACK_QUESTIONS = [
        "What was your favorite hobby growing up?",
        "Can you tell me about a family tradition you loved?",
        "What is a song that always makes you smile?",
        "What was your favorite meal that your mother used to cook?",
        "Tell me about a place you visited that you'll never forget.",
    ]

    from .base import call_llm

class InterviewerAgent:
    
    def generate_question(self, language="English", past_questions=None):
        if past_questions is None:
            past_questions = []
            
        # Create a strict rule if there is history
        avoid_str = ""
        if past_questions:
            # We only need to pass the last 5 or 6 questions to save API tokens
            recent_past = past_questions[-5:] 
            avoid_list = "\n- ".join(recent_past)
            avoid_str = f"CRITICAL RULE: You MUST NOT ask anything similar to these past questions:\n- {avoid_list}\n\n"

        system_prompt = (
            "You are a warm, empathetic cognitive-engagement companion for an elderly person. "
            "Your task is to ask a single, highly engaging, open-ended memory question to spark nostalgia and conversation. "
            "Focus on sensory details, childhood, early career, or family traditions. "
            f"{avoid_str}"
            f"Output ONLY the question in native {language} script. Do not include any conversational filler."
        )
        
        user_prompt = "Generate today's question."

        result = call_llm(system_prompt, user_prompt, max_tokens=250)
        
        if result:
            return result.strip().strip('"')
            
        # Fallback if the API fails
        return "What is a small thing that brought you joy when you were younger?"