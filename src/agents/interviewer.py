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

    def generate_question(self):
        system_prompt = (
            "You are a warm, curious companion for an elderly person. Ask one unique, "
            "thought-provoking question to spark a pleasant memory. Avoid standard tropes "
            "like 'favorite food' or 'childhood hobby'. Instead, ask about specific sensory "
            "details or small life moments (e.g., 'Do you remember the smell of rain in the "
            "summer where you grew up?'). Keep it under 20 words. No preamble, return only the question."
        )
        user_prompt = "Give me today's memory question."

        result = call_llm(system_prompt, user_prompt, max_tokens=60)
        
        if result:
            return result.strip().strip('"').strip()

        return random.choice(self.FALLBACK_QUESTIONS)