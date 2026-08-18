import pytest
import json
from unittest.mock import patch, MagicMock

from backend.agents.escalation import evaluate_escalation_need
from backend.agents.report_generator import generate_weekly_summary

# --- Test Escalation Logic ---

def test_escalation_safety_flag():
    """Tests that a single safety flag triggers an escalation immediately."""
    insights = [
        {"engagement_level": "high", "safety_flag": False},
        {"engagement_level": "high", "safety_flag": True} # Trigger
    ]
    assert evaluate_escalation_need(insights) is True

def test_escalation_three_consecutive_lows():
    """Tests that exactly 3 consecutive low engagements trigger an escalation."""
    insights = [
        {"engagement_level": "high", "safety_flag": False},
        {"engagement_level": "low", "safety_flag": False},
        {"engagement_level": "low", "safety_flag": False},
        {"engagement_level": "low", "safety_flag": False} # Trigger
    ]
    assert evaluate_escalation_need(insights) is True

def test_escalation_mixed_ignores():
    """Tests that a broken streak of lows does NOT trigger an escalation."""
    insights = [
        {"engagement_level": "low", "safety_flag": False},
        {"engagement_level": "medium", "safety_flag": False}, # Streak breaker
        {"engagement_level": "low", "safety_flag": False}
    ]
    assert evaluate_escalation_need(insights) is False

def test_escalation_empty_list():
    """Ensures robust handling of an elder with no history."""
    assert evaluate_escalation_need([]) is False

# --- Test Weekly Report Generation ---

@patch("backend.agents.report_generator.os.getenv")
@patch("backend.agents.report_generator.client.chat.completions.create")
def test_generate_weekly_summary(mock_groq_create, mock_getenv):
    """Tests that the Llama-3 response parses cleanly into the required schema."""
    mock_getenv.return_value = "fake_key"
    
    # Setup mock JSON response from LLM
    mock_response = MagicMock()
    mock_response.choices[0].message.content = json.dumps({
        "engagement_trend": "Very talkative and engaged this week.",
        "emotional_trend": "Generally positive mood.",
        "recurring_topics": ["gardening", "grandchildren"]
    })
    mock_groq_create.return_value = mock_response

    profile = {"name": "Arthur"}
    interactions = [{"interaction_date": "2026-08-15", "domain": "semantic_memory"}]
    insights = [{"engagement_level": "high", "topics": ["gardening"], "safety_flag": False}]

    result = generate_weekly_summary(profile, interactions, insights)

    assert result["engagement_trend"] == "Very talkative and engaged this week."
    assert result["emotional_trend"] == "Generally positive mood."
    assert len(result["recurring_topics"]) == 2
    assert "gardening" in result["recurring_topics"]
    
    # Ensure system prompt was sent with strict JSON format enforcement
    mock_groq_create.assert_called_once()
    _, kwargs = mock_groq_create.call_args
    assert kwargs["response_format"] == {"type": "json_object"}
    assert kwargs["temperature"] == 0.2