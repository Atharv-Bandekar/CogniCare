import pytest
from unittest.mock import patch

from backend.agents.evaluator import evaluate_response

# WHY: The HF Inference API key is present in the test env, so we patch requests.post
# to force the deterministic heuristic path (and never touch the network).

CONTRACT_KEYS = {
    "sentiment_label", "sentiment_score", "engagement_level", "engagement_score",
    "response_depth", "topics", "safety_flag", "raw_model_label",
}


@patch("backend.agents.evaluator.requests.post")
def test_contract_keys_present(mock_post):
    """evaluate_response returns every key the insights table / coordinator expect."""
    mock_post.side_effect = Exception("offline")
    result = evaluate_response("apple apple apple")
    assert CONTRACT_KEYS.issubset(result.keys())


@patch("backend.agents.evaluator.requests.post")
def test_labels_are_lowercase(mock_post):
    """engagement_level and sentiment_label must be lowercase (DB + escalation contract)."""
    mock_post.side_effect = Exception("offline")
    result = evaluate_response("I had a wonderful and happy and great day today")
    assert result["engagement_level"] == result["engagement_level"].lower()
    assert result["sentiment_label"] == result["sentiment_label"].lower()
    assert result["sentiment_label"] in {"positive", "neutral", "negative"}


@patch("backend.agents.evaluator.requests.post")
def test_engagement_thresholds(mock_post):
    """Word-count thresholds map to lowercase engagement levels."""
    mock_post.side_effect = Exception("offline")
    assert evaluate_response("apple " * 25)["engagement_level"] == "high"
    assert evaluate_response("apple " * 12)["engagement_level"] == "medium"
    assert evaluate_response("apple " * 3)["engagement_level"] == "low"
    assert evaluate_response("")["engagement_level"] == "none"


@patch("backend.agents.evaluator.requests.post")
def test_response_depth_tracks_engagement(mock_post):
    mock_post.side_effect = Exception("offline")
    assert evaluate_response("apple " * 25)["response_depth"] == "deep"
    assert evaluate_response("")["response_depth"] == "none"


@patch("backend.agents.evaluator.requests.post")
def test_positive_sentiment(mock_post):
    mock_post.side_effect = Exception("offline")
    result = evaluate_response("I feel happy and grateful, it was a wonderful and beautiful day")
    assert result["sentiment_label"] == "positive"
    assert result["sentiment_score"] > 0.15


@patch("backend.agents.evaluator.requests.post")
def test_topics_extraction_excludes_stopwords(mock_post):
    """Salient content words surface; common stopwords do not."""
    mock_post.side_effect = Exception("offline")
    text = ("My grandchildren visited and we talked about gardening. "
            "Gardening is a hobby and my grandchildren enjoy the garden.")
    topics = evaluate_response(text)["topics"]
    assert "grandchildren" in topics
    assert "gardening" in topics
    assert "and" not in topics and "about" not in topics


@patch("backend.agents.evaluator.requests.post")
def test_safety_flag_true_on_distress(mock_post):
    """Acute distress words raise the (non-clinical) safety flag."""
    mock_post.side_effect = Exception("offline")
    assert evaluate_response("I fell down near the stairs this morning")["safety_flag"] is True
    assert evaluate_response("I have chest pain and feel dizzy")["safety_flag"] is True


@patch("backend.agents.evaluator.requests.post")
def test_safety_flag_false_on_calm_text(mock_post):
    mock_post.side_effect = Exception("offline")
    result = evaluate_response("I had a lovely quiet afternoon reading by the window")
    assert result["safety_flag"] is False


@patch("backend.agents.evaluator.requests.post")
def test_empty_transcript_is_safe(mock_post):
    mock_post.side_effect = Exception("offline")
    result = evaluate_response("")
    assert result["engagement_level"] == "none"
    assert result["safety_flag"] is False
    assert result["topics"] == []
