import pytest
from unittest.mock import patch
from backend.agents.question_engine import (
    get_todays_domain,
    compute_difficulty,
    build_question_context,
    DOMAIN_ROTATION
)

def test_get_todays_domain_rotation():
    """Tests that the domain modulo arithmetic correctly wraps days > 7."""
    assert get_todays_domain(1) == DOMAIN_ROTATION[1]
    assert get_todays_domain(7) == DOMAIN_ROTATION[7]
    # Day 8 should wrap back to Day 1 logic
    assert get_todays_domain(8) == DOMAIN_ROTATION[1]

def test_compute_difficulty_thresholds():
    """Tests the DDA difficulty string calculations against the config bounds."""
    # Under 0.4 should be easy
    assert compute_difficulty([0.1, 0.3, 0.2]) == "easy"
    
    # Over 0.7 should be hard
    assert compute_difficulty([0.8, 0.9, 0.9]) == "hard"
    
    # Between bounds (0.4 - 0.7) should be medium
    assert compute_difficulty([0.5, 0.6, 0.4]) == "medium"
    
    # Edge case: No history defaults to medium
    assert compute_difficulty([]) == "medium"

@patch("backend.agents.question_engine.search_memories")
def test_build_question_context(mock_search_memories):
    """Tests that the context assembler correctly aggregates DDA and RAG data."""
    # Mocking the RAG memory store return structure
    mock_search_memories.return_value = [{"content": "Has a golden retriever."}]
    
    context = build_question_context(
        elder_id="test_uuid_123",
        cycle_day=1,
        personal_context_summary="Lives in Mumbai.",
        recent_engagement_scores=[0.8, 0.9, 0.9] # Triggers "hard" difficulty
    )
    
    assert context["difficulty"] == "hard"
    assert "retriever" in context["retrieved_memories"][0]
    assert context["personal_context_summary"] == "Lives in Mumbai."
    assert "episodic_memory" not in context["domain_description"] # Should be the description string, not the key
    
    # Verify search was called with a combined query
    mock_search_memories.assert_called_once()
    args, kwargs = mock_search_memories.call_args
    assert "Mumbai" in args[1] # The search query should contain the personal context