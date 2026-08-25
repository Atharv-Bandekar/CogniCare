import os
import json
import logging
from typing import List, Dict, Any
from groq import Groq

logger = logging.getLogger(__name__)

# WHY: We use a module-level client instantiation so it reuses connection pooling 
# across multiple Celery background job runs.
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_memorable_content(interaction_transcript: str, existing_topics: List[str]) -> List[Dict[str, Any]]:
    """
    Analyzes a conversation transcript to extract long-term social and personal memories.
    
    Args:
        interaction_transcript (str): The text of the recent conversation to analyze.
        existing_topics (List[str]): Previously known topics to prevent duplicate memory creation.
        
    Returns:
        List[Dict[str, Any]]: A list of dictionaries containing 'content' and 'category'.
                              Categories are restricted to: people, places, events, hobbies, family_stories.
    """
    # WHY: It is absolutely critical that the prompt strictly forbids medical/diagnostic data extraction.
    # This keeps our pgvector database clean of any PHI or accidental diagnostic assertions, 
    # ensuring we remain strictly a wellness and social companion.
    system_prompt = f"""
    You are an AI assistant designed to extract social and personal memories from a wellness companion's conversation.
    Your goal is to identify facts worth remembering long-term (e.g., family names, hobbies, favorite places, past life events).
    
    STRICT RULES:
    1. Do NOT extract, evaluate, or store any medical data, symptoms, cognitive assessments, or health diagnoses.
    2. Ignore transient information (e.g., "I am having lunch right now").
    3. Exclude topics the user has already mentioned heavily: {', '.join(existing_topics) if existing_topics else 'None'}.
    
    Output strictly in JSON format matching this schema:
    {{
        "memories": [
            {{
                "content": "A concise, self-contained sentence describing the memory.",
                "category": "Must be exactly one of: people, places, events, hobbies, family_stories"
            }}
        ]
    }}
    If there are no memorable facts, return an empty list for "memories".
    """

    try:
        # WHY: Llama-3 8B is sufficient and highly cost-effective for zero-shot JSON extraction tasks.
        response = client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": interaction_transcript}
            ],
            response_format={"type": "json_object"},
            temperature=0.1 # Low temperature for deterministic classification and formatting
        )
        
        raw_output = response.choices[0].message.content
        parsed = json.loads(raw_output)
        
        return parsed.get("memories", [])
        
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Groq response as JSON: {e}")
        return []
    except Exception as e:
        logger.error(f"Error during memory extraction via Groq: {e}")
        return []