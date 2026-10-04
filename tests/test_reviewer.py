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
    before = [(t.report_id, t.final_severity, t.why, t.raised) for t in queue]
    log = DecisionLog()
    for t in queue:
        log.add(decide(t, "Sam Lee", CHANGE, severity=1 if t.final_severity > 1 else 4,
                       reason="Reviewer's own view of this one."))
    after = [(t.report_id, t.final_severity, t.why, t.raised) for t in queue]
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


# ---- tally and decisions file ----

def _queue_and_ref():
    import config as _c
    from triage.fixtures import load_fixture_outcomes
    from triage.loader import load_reports
    from triage.priority import build_queue
    from triage.reference import load_reference
    ref, reports = load_reference(), load_reports()
    return build_queue(reports, load_fixture_outcomes([x.report_id for x in reports]), ref), ref


def test_the_tally_counts_each_reports_latest_decision():
    from triage import reviewer
    queue, ref = _queue_and_ref()
    log = reviewer.DecisionLog()
    t0, t1, t2, t3 = queue[0], queue[10], queue[11], queue[12]
    log.add(reviewer.decide(t0, "Sam Lee", reviewer.CONFIRM))
    log.add(reviewer.decide(t1, "Sam Lee", reviewer.CHANGE, 4, ""))                       # raised
    log.add(reviewer.decide(t2, "Sam Lee", reviewer.CHANGE, 1, "Checked with the lead."))  # lowered
    log.add(reviewer.decide(t3, "Sam Lee", reviewer.NEEDS_INFO))
    log.add(reviewer.decide(t3, "Sam Lee", reviewer.CONFIRM))                              # changed their mind: latest counts
    n = reviewer.tally(log, queue)
    assert (n.total, n.reviewed, n.confirmed, n.raised, n.lowered, n.needs_info) == (28, 4, 2, 1, 1, 0)
    assert reviewer.tally(reviewer.DecisionLog(), queue).reviewed == 0


def test_the_decisions_file_has_every_saved_decision_and_plain_columns():
    import csv, io
    from triage import reviewer, text
    queue, ref = _queue_and_ref()
    log = reviewer.DecisionLog()
    log.add(reviewer.decide(queue[0], "Sam Lee", reviewer.NEEDS_INFO))
    log.add(reviewer.decide(queue[0], "Sam Lee", reviewer.CONFIRM))
    log.add(reviewer.decide(queue[11], "Ana Roy", reviewer.CHANGE, 1, "Checked with the lead."))
    rows = list(csv.reader(io.StringIO(reviewer.decisions_csv(log, queue, ref))))
    assert tuple(rows[0]) == text.CSV_HEADERS and len(rows) == 4
    assert [r[5] for r in rows[1:]] == [text.AGREED_UNDECIDED, text.AGREED_YES, text.AGREED_NO]
    assert rows[3][0] == queue[11].report_id and rows[3][6] == "Ana Roy" and rows[3][7] == "Checked with the lead."
    assert reviewer.decisions_csv(reviewer.DecisionLog(), queue, ref).strip().count("\n") == 0   # header only


def test_typed_text_cannot_run_as_a_spreadsheet_formula():
    import csv, io
    from triage import reviewer
    queue, ref = _queue_and_ref()
    log = reviewer.DecisionLog()
    log.add(reviewer.decide(queue[11], "=HYPERLINK(1)", reviewer.CHANGE, 1, "+cmd|' /C calc'!A0"))
    row = list(csv.reader(io.StringIO(reviewer.decisions_csv(log, queue, ref))))[1]
    assert row[6].startswith("'=") and row[7].startswith("'+")
