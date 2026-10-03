"""P1: the four quality checks pass on good data and fail on deliberately broken data."""
from dataclasses import replace

from triage import text
from triage.checks import run_checks


def statuses_for(reports):
    return {r.report_id: text.STATUS_WAITING for r in reports}


def results(reports, queue, statuses):
    return {c.name: c.passed for c in run_checks(reports, queue, statuses)}


def test_all_four_pass_on_good_data(reports, queue):
    checks = run_checks(reports, queue, statuses_for(reports))
    assert len(checks) == 4 and all(c.passed for c in checks)


def test_a_report_missing_from_the_queue_fails_the_count_check(reports, queue):
    r = results(reports, queue[:-1], statuses_for(reports))
    assert not r[text.CHECK_COUNT_NAME]


def test_a_report_counted_twice_fails_the_count_check(reports, queue):
    r = results(reports, queue + [queue[0]], statuses_for(reports))
    assert not r[text.CHECK_COUNT_NAME]


def test_an_invalid_priority_fails_the_priority_check(reports, queue):
    broken = [replace(queue[0], final_severity=0)] + queue[1:]
    assert not results(reports, broken, statuses_for(reports))[text.CHECK_PRIORITY_NAME]


def test_a_failed_report_below_the_top_fails_the_priority_check(reports, queue):
    failed = next(t for t in queue if t.failed)
    broken = [replace(t, final_severity=2) if t is failed else t for t in queue]
    assert not results(reports, broken, statuses_for(reports))[text.CHECK_PRIORITY_NAME]


def test_a_shuffled_queue_fails_the_order_check(reports, queue):
    swapped = list(queue)
    swapped[0], swapped[-1] = swapped[-1], swapped[0]
    assert not results(reports, swapped, statuses_for(reports))[text.CHECK_ORDER_NAME]


def test_a_missing_status_fails_the_status_check(reports, queue):
    statuses = statuses_for(reports)
    statuses.pop(reports[3].report_id)
    assert not results(reports, queue, statuses)[text.CHECK_STATUS_NAME]
    statuses[reports[3].report_id] = ""
    assert not results(reports, queue, statuses)[text.CHECK_STATUS_NAME]


def test_each_check_fails_alone_not_all_at_once(reports, queue):
    r = results(reports, queue, {})            # no statuses at all
    assert [name for name, ok in r.items() if not ok] == [text.CHECK_STATUS_NAME]
