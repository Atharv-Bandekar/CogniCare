import pytest
from unittest.mock import patch

from backend.agents.escalation import (
    check_consecutive_negative,
    trigger_escalation_alert,
    LOW_ENGAGEMENT_THRESHOLD,
    FORBIDDEN_WORDS,
)

# --- check_consecutive_negative ---------------------------------------------


@patch("backend.agents.escalation.get_recent_engagement_scores")
def test_three_consecutive_lows_trigger(mock_scores):
    """Three low readings across the window flag sustained withdrawal."""
    mock_scores.return_value = [0.3, 0.3, 0.3]
    assert check_consecutive_negative("elder_1") is True


@patch("backend.agents.escalation.get_recent_engagement_scores")
def test_threshold_boundary_is_inclusive(mock_scores):
    """Scores exactly at the threshold still count as low."""
    mock_scores.return_value = [LOW_ENGAGEMENT_THRESHOLD] * 3
    assert check_consecutive_negative("elder_1") is True


@patch("backend.agents.escalation.get_recent_engagement_scores")
def test_mixed_streak_does_not_trigger(mock_scores):
    """A medium reading in the window breaks the low streak."""
    mock_scores.return_value = [0.3, 0.6, 0.3]
    assert check_consecutive_negative("elder_1") is False


@patch("backend.agents.escalation.get_recent_engagement_scores")
def test_insufficient_data_does_not_trigger(mock_scores):
    """Fewer readings than the required window stays conservative (no alert)."""
    mock_scores.return_value = [0.3, 0.3]
    assert check_consecutive_negative("elder_1") is False


@patch("backend.agents.escalation.get_recent_engagement_scores")
def test_empty_history_does_not_trigger(mock_scores):
    mock_scores.return_value = []
    assert check_consecutive_negative("elder_1") is False


# --- trigger_escalation_alert -----------------------------------------------


@patch("backend.agents.escalation.get_elder_profile")
def test_alert_payload_shape_and_personalization(mock_profile):
    mock_profile.return_value = {"name": "Arthur", "caregiver_user_id": "cg-1"}
    alert = trigger_escalation_alert("elder_1")

    assert alert["elder_id"] == "elder_1"
    assert alert["caregiver_user_id"] == "cg-1"
    assert alert["alert_type"] == "consecutive_low_engagement"
    assert alert["requires_delivery"] is True
    assert "Arthur" in alert["message"]


@patch("backend.agents.escalation.get_elder_profile")
def test_alert_copy_is_non_clinical(mock_profile):
    """HARD RULE: caregiver-facing copy never contains diagnostic language."""
    mock_profile.return_value = {"name": "Arthur", "caregiver_user_id": "cg-1"}
    message = trigger_escalation_alert("elder_1")["message"].lower()
    assert not any(word in message for word in FORBIDDEN_WORDS)


@patch("backend.agents.escalation.get_elder_profile")
def test_alert_handles_missing_profile(mock_profile):
    mock_profile.return_value = None
    alert = trigger_escalation_alert("elder_1")
    assert alert["caregiver_user_id"] is None
    assert "your loved one" in alert["message"]
