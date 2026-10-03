"""Confirmation check against the fixed list of flags. It never reads the report text.

The AI reader returns flags from the list in data/reference/hazard_flags.csv, plus its own rating and reason,
and it is told the list and each flag's minimum severity. The code then confirms: if the rating is below the
highest minimum among the flags, the code raises it. Code can only RAISE a severity, never lower it.
"""
from dataclasses import dataclass

from triage.models import IncidentReading
from triage.reference import HazardFlag


@dataclass(frozen=True)
class Escalation:
    floor: int                      # highest minimum among the flags found, 0 if none
    flags: tuple[str, ...]          # the flags found, most serious first
    needs_person: bool              # one of the flags says text is aimed at the reader


def check_flags(reading: IncidentReading, table: dict[str, HazardFlag]) -> Escalation:
    found = [table[f] for f in reading.hazard_flags if f in table]
    found.sort(key=lambda f: (-f.floor, f.flag_id))
    return Escalation(
        floor=max((f.floor for f in found), default=0),
        flags=tuple(f.flag_id for f in found),
        needs_person=any(f.needs_person for f in found),
    )
