"""Confirmation check against the fixed list of flags. It never reads the report text, and it never
reads a flag's detail (the detail is only for a person to read).

The AI reader returns flags from the list in data/reference/hazard_flags.csv, plus its own rating and reason,
and it is told the list and each flag's minimum severity. The code then confirms: if the rating is below the
highest minimum among the flags, the code raises it. Code can only RAISE a severity, never lower it.
"""
from dataclasses import dataclass

from triage.models import FlagFinding, IncidentReading
from triage.reference import HazardFlag


@dataclass(frozen=True)
class Escalation:
    floor: int                              # highest minimum among the flags found, 0 if none
    findings: tuple[FlagFinding, ...]       # the findings, most serious flag first
    needs_person: bool                      # one of the flags says text is aimed at the reader

    @property
    def flags(self) -> tuple[str, ...]:
        return tuple(f.flag for f in self.findings)


def check_flags(reading: IncidentReading, table: dict[str, HazardFlag]) -> Escalation:
    found = sorted((f for f in reading.hazard_flags if f.flag in table), key=lambda f: (-table[f.flag].floor, f.flag))
    return Escalation(
        floor=max((table[f.flag].floor for f in found), default=0),
        findings=tuple(found),
        needs_person=any(table[f.flag].needs_person for f in found),
    )
