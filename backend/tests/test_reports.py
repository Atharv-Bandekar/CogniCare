"""
Tests for the weekly report tasks (Phase 3B).

These tasks only handle cycle-window arithmetic and per-elder isolation; the
aggregation itself is covered by test_weekly_report.py.
"""
from datetime import date
from unittest.mock import patch

import pytest

from backend.celery_app.tasks.reports import (
    generate_all_weekly_reports,
    generate_weekly_report_for_elder,
    _last_cycle_bounds,
    CYCLE_LENGTH_DAYS,
)

MODULE = "backend.celery_app.tasks.reports"


def test_cycle_window_is_seven_days_ending_yesterday():
    """Running early Monday must summarize the finished week, not a partial day."""
    start, end = _last_cycle_bounds(today=date(2026, 8, 24))  # a Monday
    assert end == date(2026, 8, 23)      # Sunday
    assert start == date(2026, 8, 17)    # the Monday before
    assert (end - start).days + 1 == CYCLE_LENGTH_DAYS


def test_cycle_window_crosses_month_boundaries():
    start, end = _last_cycle_bounds(today=date(2026, 9, 3))
    assert end == date(2026, 9, 2)
    assert start == date(2026, 8, 27)


def test_fan_out_queues_one_report_per_elder():
    elders = [{"id": "a"}, {"id": "b"}]
    with patch(f"{MODULE}.get_all_elders", return_value=elders), \
         patch(f"{MODULE}._last_cycle_bounds", return_value=(date(2026, 8, 17), date(2026, 8, 23))), \
         patch(f"{MODULE}.generate_weekly_report_for_elder") as m_task:
        result = generate_all_weekly_reports()

    assert result["elders"] == 2
    assert result["queued"] == 2
    assert result["cycle_start"] == "2026-08-17"
    assert result["cycle_end"] == "2026-08-23"

    assert m_task.apply_async.call_count == 2
    call = m_task.apply_async.call_args
    assert call.kwargs["args"] == ["b", "2026-08-17", "2026-08-23"]
    assert call.kwargs["queue"] == "reports"


def test_fan_out_survives_a_database_failure():
    with patch(f"{MODULE}.get_all_elders", side_effect=RuntimeError("db down")), \
         patch(f"{MODULE}.generate_weekly_report_for_elder") as m_task:
        result = generate_all_weekly_reports()

    assert result["elders"] == 0
    assert result["queued"] == 0
    # Dates are still reported so the failure is diagnosable from the log.
    assert result["cycle_start"] and result["cycle_end"]
    m_task.apply_async.assert_not_called()


def test_no_elders_queues_nothing():
    with patch(f"{MODULE}.get_all_elders", return_value=[]), \
         patch(f"{MODULE}.generate_weekly_report_for_elder") as m_task:
        result = generate_all_weekly_reports()

    assert result["elders"] == 0
    assert result["queued"] == 0
    m_task.apply_async.assert_not_called()


def test_per_elder_report_delegates_to_the_generator():
    with patch(f"{MODULE}.generate_weekly_report", return_value={"id": "report-1"}) as m_gen:
        result = generate_weekly_report_for_elder("elder-1", "2026-08-17", "2026-08-23")

    assert result == {"status": "generated", "elder_id": "elder-1"}
    m_gen.assert_called_once_with("elder-1", "2026-08-17", "2026-08-23")


def test_per_elder_failure_is_retried():
    """One elder's LLM failure is retryable and must not affect the others."""
    with patch(f"{MODULE}.generate_weekly_report", side_effect=RuntimeError("llm offline")):
        with pytest.raises(Exception):
            generate_weekly_report_for_elder("elder-1", "2026-08-17", "2026-08-23")
