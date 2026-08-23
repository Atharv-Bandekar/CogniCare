"""
Tests for the scheduling tasks (Phase 3B).

Covers the due-time arithmetic (the fiddliest part of scheduling), the beat
fan-out, and the per-elder send flow including the 7-day rotation advance.
"""
import contextlib
import types
from datetime import datetime, time, timedelta
from unittest.mock import patch

import pytest

from backend.celery_app.tasks.scheduling import (
    dispatch_daily_questions,
    send_daily_question,
    is_elder_due,
    _local_now,
    _parse_time_to_minutes,
    DISPATCH_WINDOW_MINUTES,
)

MODULE = "backend.celery_app.tasks.scheduling"


class Effect:
    """Marker: patch with side_effect instead of return_value."""

    def __init__(self, value):
        self.value = value


ELDER = {
    "id": "elder-1",
    "name": "Arthur",
    "whatsapp_number": "+919000000001",
    "preferred_language": "en",
    "preferred_interaction_time": "09:00",
    "timezone": "Asia/Kolkata",
    "cycle_day": 1,
    "personal_context": {"hobby": "gardening"},
}

DEFAULTS = {
    "get_all_elders": [ELDER],
    "get_elder_profile": ELDER,
    "get_recent_engagement_scores": [0.8, 0.7, 0.9],
    "get_interactions_by_elder": [{"question": "What did you plant last spring?"}],
    "insert_daily_interaction": {"id": "interaction-1"},
    "update_elder_profile": {"id": "elder-1"},
    "get_unincorporated_family_suggestion": None,
    "mark_family_suggestion_incorporated": {"id": "fam-1"},
    "build_question_context": {"domain": "episodic_memory", "difficulty": "medium"},
    "send_whatsapp_message": {"sid": "SMout"},
}


@contextlib.contextmanager
def scheduling(**overrides):
    """Patches the scheduling module's dependencies; yields a namespace of mocks."""
    specs = {**DEFAULTS, **overrides}
    mocks = {}
    with contextlib.ExitStack() as stack:
        for name, value in specs.items():
            kwargs = {"side_effect": value.value} if isinstance(value, Effect) else {"return_value": value}
            mocks[name] = stack.enter_context(patch(f"{MODULE}.{name}", **kwargs))

        agent_cls = stack.enter_context(patch(f"{MODULE}.InterviewerAgent"))
        agent_cls.return_value.generate_question.return_value = "Arthur, what did your garden smell like?"
        mocks["InterviewerAgent"] = agent_cls
        yield types.SimpleNamespace(**mocks)


# --------------------------------------------------------------------------
# Due-time arithmetic (pure, no Celery or DB)
# --------------------------------------------------------------------------

def test_elder_is_due_inside_the_window():
    now = datetime(2026, 8, 23, 9, 0)
    assert is_elder_due({"preferred_interaction_time": "08:50"}, now=now) is True


def test_elder_is_due_exactly_on_the_minute():
    now = datetime(2026, 8, 23, 9, 0)
    assert is_elder_due({"preferred_interaction_time": "09:00"}, now=now) is True


def test_elder_is_not_due_just_before_the_window():
    now = datetime(2026, 8, 23, 9, 0)
    # 08:44 is one minute older than the 15-minute window.
    assert is_elder_due({"preferred_interaction_time": "08:44"}, now=now) is False


def test_elder_is_not_due_hours_away():
    now = datetime(2026, 8, 23, 9, 0)
    assert is_elder_due({"preferred_interaction_time": "18:30"}, now=now) is False


def test_window_wraps_around_midnight():
    """A 00:05 sweep must still catch a 23:55 preferred time."""
    now = datetime(2026, 8, 23, 0, 5)
    assert is_elder_due({"preferred_interaction_time": "23:55"}, now=now) is True
    assert is_elder_due({"preferred_interaction_time": "00:03"}, now=now) is True
    assert is_elder_due({"preferred_interaction_time": "12:00"}, now=now) is False


def test_missing_or_unparseable_time_is_never_due():
    now = datetime(2026, 8, 23, 9, 0)
    assert is_elder_due({}, now=now) is False
    assert is_elder_due({"preferred_interaction_time": None}, now=now) is False
    assert is_elder_due({"preferred_interaction_time": "not a time"}, now=now) is False


def test_every_minute_of_the_day_is_claimed_by_exactly_one_sweep():
    """
    The dispatch windows must tile the day: no gaps (a missed question) and no
    overlaps (two questions in one day).

    REGRESSION: an inclusive window start made every quarter-hour time — 09:00,
    08:45, i.e. the round times real users choose — match two consecutive sweeps.
    """
    sweeps = [datetime(2026, 8, 23, hour, minute)
              for hour in range(24) for minute in (0, 15, 30, 45)]

    double_booked, never_sent = [], []
    for minute_of_day in range(24 * 60):
        preferred = time(minute_of_day // 60, minute_of_day % 60)
        hits = sum(1 for sweep in sweeps
                   if is_elder_due({"preferred_interaction_time": preferred}, now=sweep))
        if hits > 1:
            double_booked.append(preferred.isoformat())
        elif hits == 0:
            never_sent.append(preferred.isoformat())

    assert not double_booked, f"times matching more than one sweep: {double_booked[:5]}"
    assert not never_sent, f"times matching no sweep: {never_sent[:5]}"


def test_boundary_time_belongs_to_its_own_sweep():
    """09:00 fires on the 09:00 sweep, not the following one."""
    elder = {"preferred_interaction_time": "09:00"}
    assert is_elder_due(elder, now=datetime(2026, 8, 23, 9, 0)) is True
    assert is_elder_due(elder, now=datetime(2026, 8, 23, 9, 15)) is False


def test_time_parsing_accepts_postgres_and_python_forms():
    assert _parse_time_to_minutes("09:00") == 540
    assert _parse_time_to_minutes("09:00:00") == 540
    assert _parse_time_to_minutes(time(9, 30)) == 570
    assert _parse_time_to_minutes(None) is None


def test_local_now_applies_the_india_offset_and_defaults_safely():
    delta = _local_now("Asia/Kolkata") - _local_now("UTC")
    assert timedelta(hours=5, minutes=29) < delta < timedelta(hours=5, minutes=31)

    # An unknown timezone falls back to the product default rather than crashing.
    fallback_gap = abs((_local_now("Nowhere/Unknown") - _local_now("Asia/Kolkata")).total_seconds())
    assert fallback_gap < 2


def test_window_size_matches_the_beat_interval():
    """Beat runs every 15 minutes; a mismatch would silently skip or double-send."""
    assert DISPATCH_WINDOW_MINUTES == 15


# --------------------------------------------------------------------------
# Beat fan-out
# --------------------------------------------------------------------------

def test_dispatch_queues_only_due_elders():
    elders = [{"id": "a"}, {"id": "b"}, {"id": "c"}]
    with scheduling(get_all_elders=elders):
        with patch(f"{MODULE}.is_elder_due", side_effect=lambda e, *a, **k: e["id"] in ("a", "c")):
            with patch(f"{MODULE}.send_daily_question") as m_send:
                result = dispatch_daily_questions()

    assert result == {"checked": 3, "queued": 2}
    assert m_send.apply_async.call_count == 2
    queued_ids = [call.kwargs["args"][0] for call in m_send.apply_async.call_args_list]
    assert queued_ids == ["a", "c"]
    # Per-elder work belongs on the scheduling queue.
    assert m_send.apply_async.call_args.kwargs["queue"] == "scheduling"


def test_dispatch_survives_a_database_failure():
    with scheduling(get_all_elders=Effect(RuntimeError("db down"))):
        result = dispatch_daily_questions()
    assert result == {"checked": 0, "queued": 0}


def test_dispatch_continues_after_one_bad_elder():
    """One malformed row must not cost every other elder their daily question."""
    elders = [{"id": "a"}, {"id": "b"}]
    with scheduling(get_all_elders=elders):
        with patch(f"{MODULE}.is_elder_due", side_effect=[RuntimeError("bad row"), True]):
            with patch(f"{MODULE}.send_daily_question") as m_send:
                result = dispatch_daily_questions()

    assert result == {"checked": 2, "queued": 1}
    assert m_send.apply_async.call_count == 1


# --------------------------------------------------------------------------
# Per-elder send
# --------------------------------------------------------------------------

def test_send_daily_question_happy_path():
    with scheduling() as m:
        result = send_daily_question("elder-1")

    assert result["status"] == "sent"
    assert result["elder_id"] == "elder-1"
    assert result["interaction_id"] == "interaction-1"
    # cycle_day 1 maps to the first domain in the rotation.
    assert result["domain"] == "episodic_memory"

    m.send_whatsapp_message.assert_called_once_with(
        "+919000000001", "Arthur, what did your garden smell like?"
    )


def test_missing_elder_is_reported_not_retried():
    with scheduling(get_elder_profile=None) as m:
        result = send_daily_question("ghost")

    assert result["status"] == "elder_not_found"
    m.send_whatsapp_message.assert_not_called()


def test_interaction_is_recorded_before_the_message_is_sent():
    """If the send fails we must still know what was asked."""
    order = []
    with scheduling(
        insert_daily_interaction=Effect(lambda data: order.append("insert") or {"id": "interaction-1"}),
        send_whatsapp_message=Effect(lambda *a, **k: order.append("send") or {"sid": "SMout"}),
    ):
        send_daily_question("elder-1")

    assert order == ["insert", "send"]


def test_send_failure_is_retried_after_the_question_is_stored():
    with scheduling(send_whatsapp_message=None) as m:
        with pytest.raises(Exception):
            send_daily_question("elder-1")

    m.insert_daily_interaction.assert_called_once()
    # The rotation must not advance for a question the elder never received.
    m.update_elder_profile.assert_not_called()


def test_cycle_day_advances_and_wraps_at_seven():
    with scheduling(get_elder_profile={**ELDER, "cycle_day": 3}) as m:
        send_daily_question("elder-1")
    m.update_elder_profile.assert_called_once_with("elder-1", {"cycle_day": 4})

    with scheduling(get_elder_profile={**ELDER, "cycle_day": 7}) as m:
        result = send_daily_question("elder-1")
    m.update_elder_profile.assert_called_once_with("elder-1", {"cycle_day": 1})
    assert result["domain"] == "emotional_reflection"


def test_pending_family_suggestion_is_woven_into_the_question():
    suggestion = {"id": "fam-1", "caregiver_suggestion": "Ask about his brother's visit."}
    with scheduling(get_unincorporated_family_suggestion=suggestion) as m:
        result = send_daily_question("elder-1")

    assert result["family_suggestion_used"] is True
    context = m.InterviewerAgent.return_value.generate_question.call_args.kwargs["context"]
    assert context["pending_family_context"] == "Ask about his brother's visit."
    # Marked as used only once it's actually in a delivered question.
    m.mark_family_suggestion_incorporated.assert_called_once_with("fam-1", "interaction-1")


def test_family_suggestion_is_not_marked_used_when_there_is_none():
    with scheduling() as m:
        result = send_daily_question("elder-1")

    assert result["family_suggestion_used"] is False
    m.mark_family_suggestion_incorporated.assert_not_called()


def test_recent_questions_are_passed_in_to_avoid_repeats():
    recent = [{"question": "Newest?"}, {"question": "Older?"}]
    with scheduling(get_interactions_by_elder=recent) as m:
        send_daily_question("elder-1")

    kwargs = m.InterviewerAgent.return_value.generate_question.call_args.kwargs
    # Reversed into chronological order for the prompt.
    assert kwargs["past_questions"] == ["Older?", "Newest?"]
    assert kwargs["language"] == "English"


def test_language_code_is_mapped_to_a_full_name():
    with scheduling(get_elder_profile={**ELDER, "preferred_language": "mr"}) as m:
        send_daily_question("elder-1")
    assert m.InterviewerAgent.return_value.generate_question.call_args.kwargs["language"] == "Marathi"


def test_context_build_failure_is_retried():
    with scheduling(build_question_context=Effect(RuntimeError("rag down"))) as m:
        with pytest.raises(Exception):
            send_daily_question("elder-1")
    m.send_whatsapp_message.assert_not_called()


def test_engagement_lookup_failure_degrades_to_no_history():
    with scheduling(get_recent_engagement_scores=Effect(RuntimeError("db down"))) as m:
        result = send_daily_question("elder-1")

    assert result["status"] == "sent"
    assert m.build_question_context.call_args.args[3] == []
