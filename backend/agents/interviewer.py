import logging
import random
from typing import Dict, Any, List
from .base import call_llm

logger = logging.getLogger(__name__)

class InterviewerAgent:
    """
    Orchestrates the generation of daily questions using dynamic difficulty and RAG context.
    """
    
    # Keeping the original fallback mechanism to ensure the system never fails to send a message[cite: 2].
    FALLBACK_QUESTIONS = {
        "English": [
            "What was your favorite hobby growing up?",
            "Can you tell me about a family tradition you loved?",
            "What is a song that always makes you smile?",
            "What was your favorite meal that your mother used to cook?",
            "Tell me about a place you visited that you'll never forget.",
        ],
        "Marathi": [
            "तुमची लहानपणापासून आवडत गोष्ट कोणती होती?",
            "तुमच्या कुटुंबातील कोणत्या रीतीवर तुला अभिमान वाटतो?",
            "तुला नेहमी हसवणारे गाणे कोणते आहे?",
            "तुमच्या आईने तयार केलेले आवडत्याचे पदार्थ कोणते होते?",
            "तू कुठला प्रवास केलात जो कायमचा लक्षात राहील?",
        ],
        "Hindi": [
            "आपकी बचपन की पसंदीदा शौक क्या थी?",
            "क्या आप कोई परिवार की परंपरा बता सकते हैं जो आपको प्रिय है?",
            "कौन सा गाना सुनकर आप हमेशा मुस्कुराते हैं?",
            "आपकी माँ का बनाया हुआ पसंदीदा खाना क्या था?",
            "ऐसी कौन सी जगह है जहाँ आप गए और जो हमेशा याद रहेगी?",
        ],
        "Tamil": [
            "உங்களுக்கு பிடித்த சிறு வயது பொழுதுபோக்கு என்ன?",
            "உங்கள் குடும்பத்தில் பிடித்த மரபு எதையாவது சொல்ல முடியுமா?",
            "உங்களை எப்போதும் சிரிக்க வைக்கும் பாடல் எது?",
            "உங்கள் அம்மா சமைத்த பிடித்த உணவு என்ன?",
            "நீங்கள் சென்று மறக்கமுடியாத இடம் எது?",
        ],
    }

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

        # WHY: Constructing the prompt carefully to produce a SHORT, CLEAR QUESTION
        # in the elder's preferred language. Too many competing instructions (memory
        # weaving, context collision) cause the LLM to write narrative instead of
        # asking a question.
        memory_hint = ''
        memories = context.get('retrieved_memories', [])
        if memories:
            memory_hint = f"If relevant, you may gently reference something like: {memories[0]}. But keep it brief and natural."

        system_prompt = f"""
        You are a warm, patient conversational companion for an elderly person named {elder_name}.
        Today's focus area: {context.get('domain_description')}.
        The elder's preferred language is {language}. Write the question ENTIRELY in {language}.
        Use the natural script for that language (Devanagari for Marathi/Hindi, Tamil script for Tamil).
        Personal context about the elder: {context.get('personal_context_summary')}
        {memory_hint}
        """

        if context.get('pending_family_context'):
            system_prompt += f"""
            The elder's family member asked about: {context.get('pending_family_context')}.
            Incorporate this naturally into today's question.
            """

        system_prompt += f"""
        Difficulty level: {context.get('difficulty')}.
        - easy: a short, specific question a child could answer.
        - medium: one clear topic, natural and conversational.
        - hard: invites storytelling, but still ONE question.

        FORMAT RULES (follow exactly):
        1. Output ONLY the question. No preamble, no explanation, no quotes.
        2. The output MUST end with a question mark ({"?" if language == "English" else "?"}).
        3. Maximum 2 sentences. Shorter is better.
        4. Never mention "cognitive domains," "testing," "evaluation," or anything clinical.
        5. Sound like a caring family friend, not a survey.
        {avoid_str}
        """
        
        user_prompt = "Generate today's question."

        # 600 tokens gives enough room for non-Latin scripts (Devanagari, Tamil)
        # which are tokenized more coarsely than English.
        result = call_llm(system_prompt, user_prompt, max_tokens=600)

        # Ensure question is complete (ends with ? or equivalent)
        if result and not result.rstrip().endswith(('?', '؟', '？', '।')):
            logger.warning("InterviewerAgent returned incomplete question (no question mark): %s", result[:150])
            # Try once more with explicit instruction
            result = call_llm(
                system_prompt + "\n\nIMPORTANT: End the question with a question mark (?).",
                user_prompt,
                max_tokens=400
            )
        
        if result:
            return result.strip().strip('"')
            
        # Fallback ensuring uptime if Groq API fails.
        fallback_pool = self.FALLBACK_QUESTIONS.get(language, self.FALLBACK_QUESTIONS["English"])
        return random.choice(fallback_pool)