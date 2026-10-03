"""P1: reviewer decisions sit next to the computed result and never replace it."""
import dataclasses
from datetime import datetime, timezone

import pytest

from triage import reviewer, text
from triage.reviewer import CHANGE, CONFIRM, NEEDS_INFO, DecisionError, DecisionLog, decide

NOW = datetime(2026, 10, 4, 1, 2, tzinfo=timezone.utc)


@pytest.fixture
def top(queue):
    return queue[0]            # severity 4


@pytest.fixture
def low(queue):
    return queue[-1]           # severity 1


# ---- lowering needs a written reason ----

@pytest.mark.parametrize("reason", ["", "   ", ".", "no", "abcd", "\n\t "])
def test_lowering_without_a_real_reason_is_refused(top, reason):
    with pytest.raises(DecisionError) as e:
        decide(top, "Sam Lee", CHANGE, severity=2, reason=reason)
    assert str(e.value) == text.ERR_REASON


def test_lowering_with_a_reason_is_saved_as_overruled(top):
    d = decide(top, "Sam Lee", CHANGE, severity=2, reason="Checked with the lead, it was a spare tool.", now=NOW)
    assert d.status == text.STATUS_OVERRULED and d.lowered and d.severity == 2
    assert d.at == "2026-10-04 01:02 UTC"


def test_the_overruled_wording_shows_the_name_and_the_reason(top, ref):
    d = decide(top, "Sam Lee", CHANGE, severity=2, reason="Spare tool, no damage.", now=NOW)
    shown = reviewer.describe(d, ref.scale)
    assert shown.startswith("Overruled by Sam Lee: Spare tool, no damage.")


def test_a_reason_is_not_needed_to_confirm_raise_or_ask_for_more(top, low):
    assert decide(top, "Sam Lee", CONFIRM).status == text.STATUS_CONFIRMED
    raised = decide(low, "Sam Lee", CHANGE, severity=3)
    assert raised.status == text.STATUS_RAISED and not raised.lowered
    assert decide(top, "Sam Lee", NEEDS_INFO).status == text.STATUS_NEEDS_INFO


# ---- name, severity, same-as-computed ----

@pytest.mark.parametrize("name", ["", "  ", "x"])
def test_a_name_is_always_required(top, name):
    for action in (CONFIRM, NEEDS_INFO):
        with pytest.raises(DecisionError) as e:
            decide(top, name, action)
        assert str(e.value) == text.ERR_NAME


def test_changing_to_the_same_severity_is_refused(top):
    with pytest.raises(DecisionError) as e:
        decide(top, "Sam Lee", CHANGE, severity=top.final_severity)
    assert str(e.value) == text.ERR_SAME


@pytest.mark.parametrize("bad", [None, 0, 5, "high"])
def test_an_invalid_severity_is_refused(top, bad):
    with pytest.raises(DecisionError):
        decide(top, "Sam Lee", CHANGE, severity=bad, reason="Some reason here")


def test_an_unknown_action_is_refused(top):
    with pytest.raises(DecisionError):
        decide(top, "Sam Lee", "close_it")


# ---- the computed result is never touched ----

def test_the_computed_result_is_frozen(top):
    with pytest.raises(dataclasses.FrozenInstanceError):
        top.final_severity = 1
    with pytest.raises(dataclasses.FrozenInstanceError):
        top.reasons = ()


def test_decisions_do_not_change_the_computed_result_or_the_queue_order(queue):
    before = [(t.report_id, t.final_severity, t.reasons, t.disagree) for t in queue]
    log = DecisionLog()
    for t in queue:
        log.add(decide(t, "Sam Lee", CHANGE, severity=1 if t.final_severity > 1 else 4,
                       reason="Reviewer's own view of this one."))
    after = [(t.report_id, t.final_severity, t.reasons, t.disagree) for t in queue]
    assert before == after
    assert all(log.status(t.report_id) in {text.STATUS_OVERRULED, text.STATUS_RAISED} for t in queue)


def test_a_decision_keeps_its_own_record_apart_from_the_computed_result(top):
    d = decide(top, "Sam Lee", CHANGE, severity=1, reason="Checked, a spare tool.")
    assert d.severity == 1 and top.final_severity == 4          # two separate things
    assert not hasattr(top, "reviewer")


# ---- the log is append-only ----

def test_the_log_keeps_every_decision_and_the_latest_sets_the_status(top):
    log = DecisionLog()
    assert log.status(top.report_id) == text.STATUS_WAITING and log.latest(top.report_id) is None
    log.add(decide(top, "Sam Lee", NEEDS_INFO))
    log.add(decide(top, "Sam Lee", CHANGE, severity=2, reason="Spoke to the lead, minor only."))
    log.add(decide(top, "Ana Ruiz", CONFIRM))
    assert len(log) == 3 and len(log.history(top.report_id)) == 3
    assert log.status(top.report_id) == text.STATUS_CONFIRMED
    assert [d.status for d in log.history(top.report_id)][:2] == [text.STATUS_NEEDS_INFO, text.STATUS_OVERRULED]


def test_a_decision_record_cannot_be_edited(top):
    d = decide(top, "Sam Lee", CONFIRM)
    with pytest.raises(dataclasses.FrozenInstanceError):
        d.reason = "changed afterwards"
