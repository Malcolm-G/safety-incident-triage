"""A check on the AI reader's OWN answers. It never reads the report text.

Each rule in data/reference/consistency_rules.csv says: if the reader's answer to a field has this value,
the severity should be at least this high. Code can only RAISE a severity with these, never lower it.
Because the AI reader has already understood the wording ("nobody was hurt" -> hurt: no), plain
word matching cannot cause a false alarm here.
"""
from dataclasses import dataclass

from triage.models import IncidentReading
from triage.reference import ConsistencyRule


@dataclass(frozen=True)
class Consistency:
    floor: int                      # highest minimum among the rules that matched, 0 if none
    matched: tuple[str, ...]        # every matching rule id
    deciding: tuple[str, ...]       # the matching rules that set the floor


def _answer(reading: IncidentReading, field: str) -> str:
    return getattr(reading, field)


def check_reading(reading: IncidentReading, rules: list[ConsistencyRule]) -> Consistency:
    matched = [r for r in rules if _answer(reading, r.field) == r.value]
    floor = max((r.floor for r in matched), default=0)
    return Consistency(
        floor=floor,
        matched=tuple(r.rule_id for r in matched),
        deciding=tuple(r.rule_id for r in matched if r.floor == floor),
    )
