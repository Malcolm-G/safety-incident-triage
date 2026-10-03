"""Review priority and queue order. Plain code only: the AI reader never sets these.

Rules, in short:
  * final severity = the higher of the AI reader's suggestion and the keyword floor (code only ever raises);
  * if the AI reader gave no usable answer, the report goes to the TOP (severity 4), never to "low";
  * the queue is ordered: highest severity, then failures, then disagreements, then most details missing.
"""
from triage import text
from triage.keywords import CodeRead, read_report
from triage.loader import Report
from triage.models import Failure, IncidentReading, Outcome, Triage
from triage.reference import Reference

TOP = 4


def final_severity(suggested: int | None, floor: int) -> int:
    """The review priority. Code can only RAISE the AI reader's suggestion. No usable answer means the top."""
    if suggested is None:
        return TOP
    return max(suggested, floor)


def sort_key(t: Triage) -> tuple:
    return (-t.final_severity, not t.failed, not t.disagree, -t.missing_count, t.report_id)


def _quote(words: tuple[str, ...], limit: int = 3) -> str:
    return ", ".join(f'"{w}"' for w in words[:limit])


def triage_report(report: Report, outcome: Outcome, ref: Reference, code: CodeRead | None = None) -> Triage:
    code = code or read_report(report.text, ref.keywords, ref.instruction_phrases)
    failure = outcome if isinstance(outcome, Failure) else None
    reading: IncidentReading | None = None if failure else outcome
    suggested = reading.suggested_severity if reading else None
    final = final_severity(suggested, code.floor)

    reasons: list[str] = []
    disagree = False
    if failure:
        reasons.append(text.FAILURE_REASONS[failure.value])
    else:
        if code.floor > suggested:
            disagree = True
            reasons.append(text.REASON_RAISED.format(
                suggested=ref.scale[suggested], final=ref.scale[final],
                words=_quote(code.top_hit.words) if code.top_hit else ""))
        else:
            reasons.append(text.REASON_AGREE.format(severity=ref.scale[final]))
        # Only words that suggest a SERIOUS injury count here. Plain injury words are too often
        # negated ("nobody was hurt"), and flagging those made almost every report "disagree".
        if code.serious_injury_words and reading.injury_mentioned == "no":
            disagree = True
            reasons.append(text.REASON_INJURY_CONFLICT)
        if code.damage_words and reading.damage_mentioned == "no":
            disagree = True
            reasons.append(text.REASON_DAMAGE_CONFLICT)
    if code.instruction_like:
        reasons.append(text.REASON_INSTRUCTION)
    if code.very_short:
        reasons.append(text.REASON_SHORT)
    missing = tuple(reading.missing_details) if reading else ()
    if missing:
        reasons.append(text.REASON_MISSING.format(items=", ".join(ref.details.get(m, m) for m in missing)))

    type_id = reading.incident_type if reading else "other"
    return Triage(
        report_id=report.report_id, reading=reading, failure=failure, suggested_severity=suggested,
        floor=code.floor, final_severity=final, disagree=disagree, instruction_like=code.instruction_like,
        missing=missing, incomplete=bool(missing) or code.very_short, very_short=code.very_short,
        reasons=tuple(reasons), checklist=tuple(ref.checklists.get(type_id, ref.checklists.get("other", []))),
    )


def build_queue(reports: list[Report], outcomes: dict[str, Outcome], ref: Reference) -> list[Triage]:
    """One Triage per report, ordered most urgent first. A report with no outcome counts as a failure."""
    items = [triage_report(r, outcomes.get(r.report_id, Failure.no_saved_answer), ref) for r in reports]
    return sorted(items, key=sort_key)
