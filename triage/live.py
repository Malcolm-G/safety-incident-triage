"""Live mode: read one typed-in report. Behind a passcode, with caps.

Nothing typed here is written to a file, a log or an error message, and the text is not kept after the read:
only the computed result is held in the open page. If no passcode is set, live mode does not exist.
"""
import hmac
import os
import threading
from dataclasses import dataclass
from datetime import date

from triage import reader
from triage.loader import Report
from triage.models import Triage
from triage.priority import triage_report
from triage.reference import Reference

MAX_CHARS = 2000
MAX_PER_SESSION = 5
MAX_PER_DAY = 100               # for the whole app, in memory only
MAX_BAD_PASSCODES = 5

OK, EMPTY, TOO_LONG, SESSION_LIMIT, DAY_LIMIT, NO_KEY = "ok", "empty", "too_long", "session_limit", "day_limit", "no_key"


def enabled() -> bool:
    return bool(os.environ.get("LIVE_PASSCODE"))


@dataclass
class LiveSession:
    unlocked: bool = False
    bad_tries: int = 0
    used: int = 0

    @property
    def locked_out(self) -> bool:
        return self.bad_tries >= MAX_BAD_PASSCODES


def unlock(session: LiveSession, given: str) -> bool:
    """Check the passcode in constant time. Too many wrong tries locks this session."""
    expected = os.environ.get("LIVE_PASSCODE", "")
    if not expected or session.locked_out:
        return False
    if hmac.compare_digest(given.encode(), expected.encode()):
        session.unlocked = True
        return True
    session.bad_tries += 1
    return False


_lock = threading.Lock()
_day = {"date": date.today(), "count": 0}


def _take_daily_slot() -> bool:
    with _lock:
        if _day["date"] != date.today():
            _day.update(date=date.today(), count=0)
        if _day["count"] >= MAX_PER_DAY:
            return False
        _day["count"] += 1
        return True


@dataclass(frozen=True)
class LiveResult:
    status: str
    triage: Triage | None = None


def submit(text: str, ref: Reference, session: LiveSession, make_client=None) -> LiveResult:
    """Read one report. The text goes to the reader and nowhere else."""
    if not session.unlocked:
        return LiveResult(EMPTY)
    if not text.strip():
        return LiveResult(EMPTY)
    if len(text) > MAX_CHARS:
        return LiveResult(TOO_LONG)
    if session.used >= MAX_PER_SESSION:
        return LiveResult(SESSION_LIMIT)
    if not _take_daily_slot():
        return LiveResult(DAY_LIMIT)
    try:
        client = (make_client or reader.make_client)()
    except reader.MissingKey:
        return LiveResult(NO_KEY)
    session.used += 1
    report = Report("LIVE", date.today().isoformat(), text.strip())
    outcome = reader.read_report(client, report, ref).outcome
    return LiveResult(OK, triage_report(report, outcome, ref))
