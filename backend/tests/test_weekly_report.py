import pytest
from unittest.mock import patch

from backend.reports.weekly_report import generate_weekly_report

MODULE = "backend.reports.weekly_report"

# A cycle window; interactions dated outside it must be ignored.
CYCLE_START = "2026-08-17"
CYCLE_END = "2026-08-23"


def _patches(
    profile=None,
    interactions=None,
    insights=None,
    recommendations=None,
    summary=None,
):
    """Context-manager bundle of all DB + summarizer dependencies of the orchestrator."""
    return (
        patch(f"{MODULE}.get_elder_profile", return_value=profile if profile is not None else {"name": "Arthur"}),
        patch(f"{MODULE}.get_interactions_by_elder", return_value=interactions or []),
        patch(f"{MODULE}.get_insights_by_elder", return_value=insights or []),
        patch(f"{MODULE}.get_recommendations_by_elder", return_value=recommendations or []),
        patch(f"{MODULE}.insert_weekly_report", side_effect=lambda rec: {**rec, "id": "report-1"}),
        patch(
            f"{MODULE}.generate_weekly_summary",
            return_value=summary or {
                "engagement_trend": "Engaged and talkative.",
                "emotional_trend": "Generally positive.",
                "recurring_topics": ["gardening", "grandchildren"],
            },
        ),
    )


def test_happy_path_assembles_full_record():
    interactions = [
        {"interaction_date": "2026-08-19", "domain": "episodic_memory"},
        {"interaction_date": "2026-08-18", "domain": "semantic_memory"},
        {"interaction_date": "2026-07-01", "domain": "old_domain"},  # out of window
    ]
    insights = [{"engagement_level": "high", "topics": ["gardening"], "safety_flag": False}]
    recommendations = [
        {"created_at": "2026-08-18T10:00:00", "status": "acted"},
        {"created_at": "2026-08-19T10:00:00", "status": "pending"},
        {"created_at": "2026-07-01T10:00:00", "status": "acted"},  # out of window
    ]

    p_profile, p_inter, p_ins, p_rec, p_insert, p_sum = _patches(
        interactions=interactions, insights=insights, recommendations=recommendations
    )
    with p_profile, p_inter, p_ins, p_rec as m_rec, p_insert as m_insert, p_sum as m_sum:
        result = generate_weekly_report("elder_1", CYCLE_START, CYCLE_END)

    assert result["elder_id"] == "elder_1"
    assert result["cycle_start"] == CYCLE_START
    assert result["cycle_end"] == CYCLE_END
    assert result["engagement_trend"] == "Engaged and talkative."
    assert result["emotional_trend"] == "Generally positive."
    assert result["recurring_topics"] == ["gardening", "grandchildren"]

    # Only in-window domains, deduped + sorted
    assert result["domains_completed"] == ["episodic_memory", "semantic_memory"]

    # Family engagement counts only in-window recommendations
    assert result["family_engagement"]["recommendations_sent"] == 2
    assert result["family_engagement"]["recommendations_acted_on"] == 1

    # Summarizer received only the two in-window interactions
    m_sum.assert_called_once()
    _, called_interactions, _ = m_sum.call_args.args
    assert len(called_interactions) == 2
    m_insert.assert_called_once()


def test_no_activity_skips_llm_and_emits_placeholder():
    p_profile, p_inter, p_ins, p_rec, p_insert, p_sum = _patches(
        interactions=[], insights=[]
    )
    with p_profile, p_inter, p_ins, p_rec, p_insert as m_insert, p_sum as m_sum:
        result = generate_weekly_report("elder_1", CYCLE_START, CYCLE_END)

    # LLM summarizer must NOT be called when there's nothing to summarize
    m_sum.assert_not_called()
    assert result["engagement_trend"] == "No interactions were recorded this cycle."
    assert result["recurring_topics"] == []
    assert result["domains_completed"] == []
    m_insert.assert_called_once()
