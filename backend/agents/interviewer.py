import random
from typing import Dict, Any, List
from .base import call_llm

class InterviewerAgent:
    """
    Orchestrates the generation of daily questions using dynamic difficulty and RAG context.
    """
    
    # Keeping the original fallback mechanism to ensure the system never fails to send a message[cite: 2].
    FALLBACK_QUESTIONS = [
        "What was your favorite hobby growing up?",
        "Can you tell me about a family tradition you loved?",
        "What is a song that always makes you smile?",
        "What was your favorite meal that your mother used to cook?",
        "Tell me about a place you visited that you'll never forget.",
    ]

    def generate_question(self, elder_name: str, language: str, context: Dict[str, Any], past_questions: List[str] = None) -> str:
        """
        Generates a tailored, context-aware question based on the elder's DDA profile and retrieved memories.
        
        Args:
            elder_name (str): The elder's name for personalization.
            language (str): The target language (e.g., "Hindi", "Marathi", "English").
            context (Dict[str, Any]): The structured context dictionary built by question_engine.py.
            past_questions (List[str], optional): Recent questions to avoid repeating.
            
        Returns:
            str: The generated question text in the target language.
        """
        if past_questions is None:
            past_questions = []
            
        avoid_str = ""
        if past_questions:
            recent_past = past_questions[-5:] 
            avoid_list = "\n- ".join(recent_past)
            avoid_str = f"CRITICAL RULE: You MUST NOT ask anything similar to these past questions:\n- {avoid_list}\n\n"

        # WHY: Constructing the prompt carefully using the blueprint template to ensure 
        # strict guardrails against clinical phrasing while utilizing DDA.
        system_prompt = f"""
        You are a warm, patient conversational companion for an elderly person named {elder_name}.
        Today's focus area is: {context.get('domain_description')}.
        The elder's preferred language is {language} — respond ONLY in that language, using natural
        script (no Latin-letter English words mixed into Hindi/Marathi/Tamil unless it's a proper noun).

        Known personal context: {context.get('personal_context_summary')}
        Relevant past memories to weave in naturally (do NOT just repeat them, build on them): {', '.join(context.get('retrieved_memories', []))}
        """

        if context.get('pending_family_context'):
            system_prompt += f"""
            The elder's family member asked about: {context.get('pending_family_context')}.
            Incorporate this naturally into today's question.
            """

        system_prompt += f"""
        Difficulty level: {context.get('difficulty')}.
        - easy: ask a concrete, specific, low-effort question. Multiple-choice style is acceptable.
        - medium: open but scoped question, one clear topic.
        - hard: open-ended, multi-step, invites storytelling and elaboration.

        Rules:
        - Never mention "cognitive domains," "testing," "evaluation," or anything clinical.
        - Sound like a caring family friend, not a survey.
        - One question only, 1-3 sentences.
        - If using a memory, create "context collision": connect the old memory to a NEW angle,
          don't just restate it.
        {avoid_str}
        - Output ONLY the question text in {language}. No preamble, no quotes, no explanation.
        """
        
        user_prompt = "Generate today's question."

        # Reusing the existing base LLM caller utility[cite: 2].
        result = call_llm(system_prompt, user_prompt, max_tokens=400)

        # Ensure question is complete (ends with ? or equivalent)
        if result and not result.rstrip().endswith(('?', '؟', '？', '।', '?', '？')):
            logger.warning("InterviewerAgent returned incomplete question: %s", result[:100])
            # Try once more with explicit instruction
            result = call_llm(
                system_prompt + "\n\nIMPORTANT: End the question with a question mark (?).",
                user_prompt,
                max_tokens=400
            )
        
        if result:
            return result.strip().strip('"')
            
        # Fallback ensuring uptime if Groq API fails[cite: 2].
        return random.choice(self.FALLBACK_QUESTIONS)