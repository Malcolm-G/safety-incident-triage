"""The AI reader's fixed fields, and the result types the rules produce.

IncidentReading is the ONLY thing the AI reader may return. It has no field for advice, an action,
a priority or a notification, and extra fields are refused. Its flags come from a fixed list
(data/reference/hazard_flags.csv); the code checks that list and can only raise a severity.
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
HazardFlagId = Literal[
    "serious_injury", "fire_or_smoke", "someone_hurt", "aircraft_damaged", "touched_aircraft",
    "moved_by_jet_blast", "fuel_leaking", "property_damaged", "injury_unclear", "nearly_struck",
    "instructions_to_reader",
]


class IncidentReading(BaseModel):
    model_config = ConfigDict(extra="forbid")

    report_id: str
    incident_type: IncidentTypeId
    suggested_severity: Literal[1, 2, 3, 4]
    rating_reason: str                      # one sentence: why this rating
    hazard_flags: list[HazardFlagId]        # things found, from the fixed list (empty if none)
    missing_details: list[DetailId]
    summary: str                            # one sentence: what happened

    @field_validator("rating_reason", "summary")
    @classmethod
    def _one_short_sentence(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        if len(v) > 300:
            raise ValueError("must be at most 300 characters")
        return v

    @field_validator("missing_details", "hazard_flags")
    @classmethod
    def _no_repeats(cls, v: list[str]) -> list[str]:
        if len(set(v)) != len(v):
            raise ValueError("must not repeat an item")
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
    reading: IncidentReading | None     # what the AI reader said (None if it failed)
    failure: Failure | None
    suggested_severity: int | None
    floor: int                          # minimum from the fixed flag list, 0 if no flag applies
    final_severity: int                 # the review priority: 1 to 4 (needs-a-person reports are always 4)
    raised: bool                        # the fixed list raised the AI reader's severity
    instruction_like: bool              # the text (or the AI reader) says it aims instructions at the reader
    flags: tuple[str, ...]              # the flags the AI reader found
    missing: tuple[str, ...]            # missing detail ids, as marked by the AI reader
    incomplete: bool
    very_short: bool
    why: tuple[str, ...]                # the clear reasons this report is where it is
    notes: tuple[str, ...]              # other notes: very short, details missing
    checklist: tuple[str, ...]          # generic reviewer checklist for the incident type

    @property
    def failed(self) -> bool:
        return self.failure is not None

    @property
    def needs_person(self) -> bool:
        """The AI reader's answer cannot be trusted for this report (no usable answer, or text aimed at the
        reader), so a person must read it now."""
        return self.failed or self.instruction_like

    @property
    def missing_count(self) -> int:
        return len(self.missing)
