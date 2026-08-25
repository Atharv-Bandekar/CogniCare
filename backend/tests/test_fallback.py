"""
Tests for the fallback sweep (Phase 3B).

A caregiver recommendation left 'pending' for 12+ hours is assumed missed and
retired to 'timed_out' so the dashboard stays honest.
"""
from unittest.mock import patch

from backend.celery_app.tasks.fallback import (
    expire_stale_recommendations,
    FALLBACK_TIMEOUT_HOURS,
    TIMED_OUT_STATUS,
)

MODULE = "backend.celery_app.tasks.fallback"


def test_default_timeout_matches_the_blueprint():
    assert FALLBACK_TIMEOUT_HOURS == 12
    # The schema's status CHECK constraint already permits this value.
    assert TIMED_OUT_STATUS == "timed_out"


def test_all_stale_recommendations_are_expired():
    stale = [{"id": "rec-1"}, {"id": "rec-2"}, {"id": "rec-3"}]
    with patch(f"{MODULE}.get_pending_recommendations_older_than", return_value=stale) as m_query, \
         patch(f"{MODULE}.update_recommendation_status") as m_update:
        result = expire_stale_recommendations()

    assert result == {"found": 3, "expired": 3}
    m_query.assert_called_once_with(FALLBACK_TIMEOUT_HOURS)
    assert m_update.call_count == 3
    assert m_update.call_args.args == ("rec-3", "timed_out")


def test_custom_timeout_is_passed_through():
    with patch(f"{MODULE}.get_pending_recommendations_older_than", return_value=[]) as m_query, \
         patch(f"{MODULE}.update_recommendation_status"):
        result = expire_stale_recommendations(timeout_hours=6)

    m_query.assert_called_once_with(6)
    assert result == {"found": 0, "expired": 0}


def test_nothing_stale_is_a_no_op():
    with patch(f"{MODULE}.get_pending_recommendations_older_than", return_value=[]), \
         patch(f"{MODULE}.update_recommendation_status") as m_update:
        result = expire_stale_recommendations()

    assert result == {"found": 0, "expired": 0}
    m_update.assert_not_called()


def test_query_failure_returns_zeroes_instead_of_raising():
    """A failed sweep should be logged, not retried forever — beat runs again in an hour."""
    with patch(f"{MODULE}.get_pending_recommendations_older_than", side_effect=RuntimeError("db down")), \
         patch(f"{MODULE}.update_recommendation_status") as m_update:
        result = expire_stale_recommendations()

    assert result == {"found": 0, "expired": 0}
    m_update.assert_not_called()


def test_one_bad_row_does_not_stop_the_sweep():
    stale = [{"id": "rec-1"}, {"id": "rec-2"}, {"id": "rec-3"}]
    with patch(f"{MODULE}.get_pending_recommendations_older_than", return_value=stale), \
         patch(f"{MODULE}.update_recommendation_status",
               side_effect=[None, RuntimeError("row vanished"), None]) as m_update:
        result = expire_stale_recommendations()

    assert result == {"found": 3, "expired": 2}
    assert m_update.call_count == 3


def test_rows_without_an_id_are_skipped():
    stale = [{"id": "rec-1"}, {}, None]
    with patch(f"{MODULE}.get_pending_recommendations_older_than", return_value=stale), \
         patch(f"{MODULE}.update_recommendation_status") as m_update:
        result = expire_stale_recommendations()

    assert result == {"found": 3, "expired": 1}
    m_update.assert_called_once_with("rec-1", "timed_out")
