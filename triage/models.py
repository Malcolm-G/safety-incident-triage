"""The AI reader's fixed fields, and the result types the rules produce.

IncidentReading is the ONLY thing the AI reader may return. It has no field for advice, an action,
a priority or a notification, and extra fields are refused.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator

IncidentTypeId = Literal[
    "aircraft_contact", "manual_handling", "slip_trip_fall", "fuel_spill", "near_miss",
    "foreign_object_debris", "equipment_fault", "jet_blast", "other",
]
DetailId = Literal["who", "where", "when", "what_happened", "injury_stated", "damage_stated", "action_taken"]
YesNoUnclear = Literal["yes", "no", "unclear"]


class IncidentReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    incident_type: IncidentTypeId
    suggested_severity: Literal[1, 2, 3, 4]
    missing_details: list[DetailId]
    injury_mentioned: YesNoUnclear
    damage_mentioned: YesNoUnclear
    summary: str

    @field_validator("summary")
    @classmethod
    def _one_short_sentence(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("summary must not be empty")
        if len(v) > 300:
            raise ValueError("summary must be at most 300 characters")
        return v

    @field_validator("missing_details")
    @classmethod
    def _no_repeats(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("missing_details must not repeat an item")
        return v


class Failure(str, Enum):
    """Why there is no usable answer from the AI reader. Every one of these goes UP the queue."""
    invalid_answer = "invalid_answer"
    wrong_report = "wrong_report"
    timed_out = "timed_out"
    refused = "refused"
    service_error = "service_error"
    no_saved_answer = "no_saved_answer"


# What the AI reader produced for one report: a reading, or the reason there is none.
Outcome = IncidentReading | Failure


@dataclass(frozen=True)
class Triage:
    """The computed result for one report. Frozen: nothing, including a reviewer, can change it."""
    report_id: str
    reading: IncidentReading | None     # what the AI reader suggested (None if it failed)
    failure: Failure | None
    suggested_severity: int | None
    floor: int                          # 0 if no keyword group matched
    final_severity: int                 # the review priority: 1 to 4 (failures are always 4)
    disagree: bool                      # the rules and the AI reader do not agree
    instruction_like: bool              # the text looks like instructions aimed at the reader
    missing: tuple[str, ...]            # missing detail ids, as marked by the AI reader
    incomplete: bool
    very_short: bool
    reasons: tuple[str, ...]            # plain-language reasons, in order
    checklist: tuple[str, ...]          # generic reviewer checklist for the incident type

    @property
    def failed(self) -> bool:
        return self.failure is not None

    @property
    def missing_count(self) -> int:
        return len(self.missing)
