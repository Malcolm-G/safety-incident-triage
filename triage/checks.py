"""Four quality checks on the queue. They catch mistakes in how the page is put together.
They cannot tell whether a judgment is right. Each check is written without calling the sorting code."""
from dataclasses import dataclass

from triage import text
from triage.loader import Report
from triage.models import Triage


@dataclass(frozen=True)
class Check:
    name: str
    passed: bool
    detail: str


def _order_problems(queue: list[Triage]) -> int:
    """Count neighbours that are in the wrong order, spelling the ordering rule out by hand."""
    def rank(t: Triage):
        return (-t.final_severity, 0 if t.needs_person else 1, 0 if t.disagree else 1, -t.missing_count, t.report_id)
    return sum(1 for a, b in zip(queue, queue[1:]) if rank(a) > rank(b))


def run_checks(reports: list[Report], queue: list[Triage], statuses: dict[str, str]) -> list[Check]:
    report_ids = [r.report_id for r in reports]
    queued_ids = [t.report_id for t in queue]
    in_queue = len(queued_ids) == len(report_ids) and sorted(queued_ids) == sorted(report_ids)

    bad_priority = [t for t in queue if t.final_severity not in (1, 2, 3, 4)]
    # a report that needs a person (no usable answer, or planted instructions) must never sit below the top
    bad_priority += [t for t in queue if t.needs_person and t.final_severity != 4]

    order_bad = _order_problems(queue)
    missing_status = [rid for rid in report_ids if not statuses.get(rid)]

    return [
        Check(text.CHECK_COUNT_NAME, in_queue,
              text.CHECK_COUNT_DETAIL.format(reports=len(report_ids), queued=len(queued_ids))),
        Check(text.CHECK_PRIORITY_NAME, not bad_priority, text.CHECK_PRIORITY_DETAIL.format(bad=len(bad_priority))),
        Check(text.CHECK_ORDER_NAME, order_bad == 0, text.CHECK_ORDER_DETAIL.format(bad=order_bad)),
        Check(text.CHECK_STATUS_NAME, not missing_status, text.CHECK_STATUS_DETAIL.format(bad=len(missing_status))),
    ]
