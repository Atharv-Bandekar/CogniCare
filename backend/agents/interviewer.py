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
    
    def generate_question(self, language: str, past_questions: list, topic: str = None) -> str:
        # ... your existing code ...
        if past_questions is None:
            past_questions = []
            
        avoid_str = ""
        if past_questions:
            recent_past = past_questions[-5:] 
            avoid_list = "\n- ".join(recent_past)
            avoid_str = f"CRITICAL RULE: You MUST NOT ask anything similar to these past questions:\n- {avoid_list}\n\n"

        # Explicit Vocabulary Enforcements to prevent LLM hallucination between Hindi and Marathi
        language_enforcement = f"CRITICAL: You MUST generate the question STRICTLY in {language}. "
        if language.lower() == "hindi":
            language_enforcement += "You must use pure Hindi vocabulary (e.g., 'Aapka', 'Kya', 'Kaise'). ABSOLUTELY DO NOT use Marathi words (e.g., 'Tumcha', 'Kay', 'Kasa')."
        elif language.lower() == "marathi":
            language_enforcement += "You must use pure Marathi vocabulary (e.g., 'Tumcha', 'Kay', 'Kasa'). ABSOLUTELY DO NOT use Hindi words (e.g., 'Aapka', 'Kya', 'Kaise')."

        # strict topic instruction first
        topic_instruction = f"CRITICAL: The question MUST be about this specific topic: '{topic}'." if topic else ""

        # updated system prompt with aggressive language guardrails
        system_prompt = (
            "You are a warm, empathetic cognitive-engagement companion for an elderly person. "
            "Your task is to ask a single, highly engaging, open-ended memory question to spark nostalgia and conversation. "
            f"{topic_instruction} "
            "Focus on sensory details and positive emotions. "
            f"{avoid_str} "
            f"CRITICAL: You must output the final question strictly and exclusively in 100% pure {language} script. "
            "Do NOT mix, embed, or hallucinate any English letters (A-Z), Latin characters, or transliteration inside the regional text. "
            "Ensure flawless spelling and grammar. "
            f"Output ONLY the question in native {language}. Do not include any conversational filler."
        )
        
        user_prompt = "Generate today's question."

        result = call_llm(system_prompt, user_prompt, max_tokens=250)
        
        if result:
            return result.strip().strip('"')
            
        return random.choice(self.FALLBACK_QUESTIONS)