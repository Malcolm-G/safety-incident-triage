"""Review priority and queue order. Plain code only: the AI reader never sets these.

Rules, in short:
  * final severity = the higher of the AI reader's rating and the minimum from the fixed flag list
    (the code only ever confirms or raises);
  * if there is no usable answer, or the report is aimed at the reader with instructions, the report goes to
    the TOP (severity 4) as "needs a person now", never to "low";
  * the queue is ordered: highest severity, then needs-a-person, then raised, then most details missing.
"""
from triage import text
from triage.escalation import check_flags
from triage.loader import Report
from triage.models import Failure, IncidentReading, Outcome, Triage
from triage.reference import Reference
from triage.textcheck import TextRead, read_text

TOP = 4


def final_severity(suggested: int | None, floor: int) -> int:
    """The review priority. Code can only RAISE the AI reader's rating. No usable answer means the top."""
    if suggested is None:
        return TOP
    return max(suggested, floor)


def sort_key(t: Triage) -> tuple:
    return (-t.final_severity, not t.needs_person, not t.raised, -t.missing_count, t.report_id)


def triage_report(report: Report, outcome: Outcome, ref: Reference, text_read: TextRead | None = None) -> Triage:
    text_read = text_read or read_text(report.text, ref.instruction_phrases)
    failure = outcome if isinstance(outcome, Failure) else None
    reading: IncidentReading | None = None if failure else outcome
    suggested = reading.suggested_severity if reading else None

    escalation = check_flags(reading, ref.hazard_flags) if reading else None
    floor = escalation.floor if escalation else 0
    final = final_severity(suggested, floor)
    instruction_like = text_read.instruction_like or bool(escalation and escalation.needs_person)
    if instruction_like:
        final = TOP                      # the reader's answer cannot be trusted for this report
    raised = bool(reading) and floor > suggested

    # the clear reasons this report is where it is
    why: list[str] = []
    if failure:
        why.append(text.FAILURE_REASONS[failure.value])
    if instruction_like:
        why.append(text.REASON_INSTRUCTION)
    flags = escalation.flags if escalation else ()
    shown = [text.FLAG_LABELS[f] for f in flags if not ref.hazard_flags[f].needs_person]
    why.extend(shown)
    if reading and not shown and not instruction_like:
        why.append(reading.rating_reason)      # nothing on the list was found: the AI reader's own reason

    notes: list[str] = []
    if text_read.very_short:
        notes.append(text.NOTE_SHORT)
    missing = tuple(reading.missing_details) if reading else ()
    if missing:
        notes.append(text.NOTE_MISSING.format(items=", ".join(ref.details.get(m, m) for m in missing)))

    type_id = reading.incident_type if reading else "other"
    return Triage(
        report_id=report.report_id, reading=reading, failure=failure, suggested_severity=suggested,
        floor=floor, final_severity=final, raised=raised, instruction_like=instruction_like, flags=tuple(flags),
        missing=missing, incomplete=bool(missing) or text_read.very_short, very_short=text_read.very_short,
        why=tuple(why), notes=tuple(notes),
        checklist=tuple(ref.checklists.get(type_id, ref.checklists.get("other", []))),
    )


def build_queue(reports: list[Report], outcomes: dict[str, Outcome], ref: Reference) -> list[Triage]:
    """One Triage per report, ordered most urgent first. A report with no outcome counts as a failure."""
    items = [triage_report(r, outcomes.get(r.report_id, Failure.no_saved_answer), ref) for r in reports]
    return sorted(items, key=sort_key)
