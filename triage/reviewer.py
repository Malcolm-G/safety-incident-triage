"""Reviewer decisions. They sit NEXT TO the computed result and never replace it.

A decision is a frozen record. The log only ever gets new records added; nothing is edited or removed.
Lowering a severity below the computed review priority needs a written reason. Nothing is kept after the session.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone

from triage import text
from triage.models import Triage

MIN_REASON_CHARS = 5
MIN_NAME_CHARS = 2

CONFIRM = "confirm"
CHANGE = "change"
NEEDS_INFO = "needs_info"


class DecisionError(ValueError):
    """The decision cannot be saved. The message is plain language for the reviewer."""


@dataclass(frozen=True)
class Decision:
    report_id: str
    reviewer: str
    action: str          # confirm | change | needs_info
    severity: int        # the severity the reviewer records
    reason: str
    at: str              # UTC time written by the code
    status: str          # one of the STATUS_* words in text.py
    lowered: bool


def _clean(value: str) -> str:
    return " ".join((value or "").split())


def decide(triage: Triage, reviewer: str, action: str, severity: int | None = None,
           reason: str = "", now: datetime | None = None) -> Decision:
    name = _clean(reviewer)
    if len(name) < MIN_NAME_CHARS:
        raise DecisionError(text.ERR_NAME)
    why = _clean(reason)
    computed = triage.final_severity

    if action == CONFIRM:
        chosen, status = computed, text.STATUS_CONFIRMED
    elif action == NEEDS_INFO:
        chosen, status = computed, text.STATUS_NEEDS_INFO
    elif action == CHANGE:
        if severity not in (1, 2, 3, 4):
            raise DecisionError(text.ERR_SEVERITY)
        if severity == computed:
            raise DecisionError(text.ERR_SAME)
        chosen = severity
        status = text.STATUS_RAISED if severity > computed else text.STATUS_OVERRULED
    else:
        raise DecisionError(text.ERR_SEVERITY)

    lowered = chosen < computed
    if lowered and len(why) < MIN_REASON_CHARS:
        raise DecisionError(text.ERR_REASON)

    stamp = (now or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC")
    return Decision(triage.report_id, name, action, chosen, why, stamp, status, lowered)


def describe(d: Decision, scale: dict[int, str]) -> str:
    if d.status == text.STATUS_OVERRULED:
        return text.DECISION_OVERRULED.format(name=d.reviewer, reason=d.reason, time=d.at)
    if d.status == text.STATUS_RAISED:
        return text.DECISION_RAISED.format(severity=scale[d.severity], name=d.reviewer, time=d.at)
    if d.status == text.STATUS_NEEDS_INFO:
        return text.DECISION_NEEDS_INFO.format(name=d.reviewer, time=d.at)
    return text.DECISION_CONFIRMED.format(name=d.reviewer, time=d.at)


@dataclass
class DecisionLog:
    """Append-only list of decisions for this session."""
    _items: list[Decision] = field(default_factory=list)

    def add(self, decision: Decision) -> None:
        self._items.append(decision)

    def history(self, report_id: str) -> list[Decision]:
        return [d for d in self._items if d.report_id == report_id]

    def latest(self, report_id: str) -> Decision | None:
        h = self.history(report_id)
        return h[-1] if h else None

    def status(self, report_id: str) -> str:
        d = self.latest(report_id)
        return d.status if d else text.STATUS_WAITING

    def __len__(self) -> int:
        return len(self._items)
