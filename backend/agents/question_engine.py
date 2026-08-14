from typing import List, Dict, Any, Tuple
from backend.config.dda_thresholds import (
    LOW_ENGAGEMENT_THRESHOLD,
    HIGH_ENGAGEMENT_THRESHOLD,
)

# TODO: @rag-dev verify this import path matches Phase 1A implementation
from backend.rag.memory_store import search_memories

# WHY: We map the 7-day cognitive cycle strictly to integer days so the Celery beat 
# scheduler can easily advance the elder's profile cycle_day (mod 7) without complex state.
DOMAIN_ROTATION: Dict[int, Tuple[str, str]] = {
    1: ("episodic_memory", "recalling specific past events, sensory details, and personal experiences"),
    2: ("semantic_memory", "drawing on lifelong knowledge, traditions, and historical events"),
    3: ("language", "exercising vocabulary, naming familiar objects, and playful word recall"),
    4: ("attention", "focusing on present-moment observations and sensory surroundings"),
    5: ("executive_function", "lightly planning simple, everyday scenarios or tasks"),
    6: ("social_memory", "reflecting on important relationships and shared moments"),
    7: ("emotional_reflection", "gentle reflection on positive feelings, pride, and gratitude")
}

def get_todays_domain(cycle_day: int) -> Tuple[str, str]:
    """
    Retrieves the cognitive domain and its description for the current cycle day.
    
    Args:
        cycle_day (int): The current day in the elder's 7-day rotation (1-7).
        
    Returns:
        Tuple[str, str]: The domain key and its descriptive system prompt instructions.
    """
    # WHY: Normalizing using modulo ensures that if a day > 7 is passed, it wraps correctly.
    normalized_day = ((cycle_day - 1) % 7) + 1
    return DOMAIN_ROTATION[normalized_day]

def compute_difficulty(recent_engagement_scores: List[float]) -> str:
    """
    Determines the interaction difficulty based on recent engagement trends.
    
    Args:
        recent_engagement_scores (List[float]): The elder's most recent engagement scores (0.0 to 1.0).
        
    Returns:
        str: "easy", "medium", or "hard".
    """
    if not recent_engagement_scores:
        # WHY: Default to medium if we have no historical data for a new user.
        return "medium"
        
    avg_score = sum(recent_engagement_scores) / len(recent_engagement_scores)
    
    if avg_score < LOW_ENGAGEMENT_THRESHOLD:
        return "easy"
    elif avg_score > HIGH_ENGAGEMENT_THRESHOLD:
        return "hard"
    return "medium"

def build_question_context(
    elder_id: str, 
    cycle_day: int, 
    personal_context_summary: str, 
    recent_engagement_scores: List[float]
) -> Dict[str, Any]:
    """
    Assembles the complete state required by the Interviewer Agent to generate a contextual question.
    
    Args:
        elder_id (str): Unique identifier for the user.
        cycle_day (int): Current day in the cognitive cycle.
        personal_context_summary (str): Static background info (e.g., hometown, family structure).
        recent_engagement_scores (List[float]): Recent scores for DDA calculation.
        
    Returns:
        Dict[str, Any]: A structured dictionary containing domain, difficulty, memories, and context.
    """
    domain_key, domain_desc = get_todays_domain(cycle_day)
    difficulty = compute_difficulty(recent_engagement_scores)
    
    # WHY: We combine the domain and static personal context to form the semantic search query, 
    # ensuring the retrieved memories are hyper-relevant to today's topic.
    search_query = f"{domain_desc}. {personal_context_summary}"
    memories = search_memories(elder_id, search_query, top_k=3)
    
    # TODO: @integration-dev (Phase 3) Fetch pending family suggestion from family_interactions
    pending_family_context = None 
    
    # TODO: @integration-dev (Phase 3) Fetch yesterday's interaction summary to prevent topic collision
    last_interaction_summary = None 

    return {
        "domain_description": domain_desc,
        "difficulty": difficulty,
        "personal_context_summary": personal_context_summary,
        "retrieved_memories": [m.get("content") for m in memories],
        "pending_family_context": pending_family_context,
        "last_interaction_summary": last_interaction_summary
    }