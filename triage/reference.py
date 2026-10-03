"""Loads the visible reference tables in data/reference/. All of them are illustrative examples.

Each loader checks its file and refuses to continue on a bad row, so a typo in a table
cannot quietly weaken a rule.
"""
import csv
from dataclasses import dataclass

import config

LEVELS = (1, 2, 3, 4)


@dataclass(frozen=True)
class SeverityLevel:
    level: int
    name: str
    meaning: str


@dataclass(frozen=True)
class IncidentType:
    id: str
    name: str
    description: str


@dataclass(frozen=True)
class HazardFlag:
    """One thing the AI reader can flag. If it flags this, the severity must be at least `floor`."""
    flag_id: str
    floor: int
    needs_person: bool      # text aimed at the reader: a person must read the report now
    definition: str         # the wording given to the AI reader


@dataclass(frozen=True)
class RequiredDetail:
    id: str
    label: str


def _rows(filename: str) -> list[dict]:
    with (config.REFERENCE_DIR / filename).open(newline="", encoding="utf-8-sig") as f:
        return [{k: (v or "").strip() for k, v in row.items()} for row in csv.DictReader(f)]


def _level(value: str, where: str) -> int:
    try:
        level = int(value)
    except ValueError:
        raise ValueError(f"{where}: severity must be a whole number, got {value!r}") from None
    if level not in LEVELS:
        raise ValueError(f"{where}: severity must be 1 to 4, got {level}")
    return level


def load_severity_scale() -> list[SeverityLevel]:
    scale = [SeverityLevel(_level(r["level"], "severity_scale.csv"), r["name"], r["meaning"])
             for r in _rows("severity_scale.csv")]
    if [s.level for s in scale] != list(LEVELS):
        raise ValueError("severity_scale.csv must list levels 1, 2, 3 and 4 once each, in order")
    return scale


def load_incident_types() -> list[IncidentType]:
    types = [IncidentType(r["id"], r["name"], r["description"]) for r in _rows("incident_types.csv")]
    if len({t.id for t in types}) != len(types):
        raise ValueError("incident_types.csv has a repeated id")
    return types


def load_hazard_flags() -> list[HazardFlag]:
    flags = []
    for r in _rows("hazard_flags.csv"):
        where = f"hazard_flags.csv ({r['flag_id']})"
        if r["needs_person"] not in {"yes", "no"}:
            raise ValueError(f"{where}: needs_person must be yes or no")
        if not r["definition"]:
            raise ValueError(f"{where}: every flag needs a definition for the AI reader")
        flags.append(HazardFlag(r["flag_id"], _level(r["floor"], where), r["needs_person"] == "yes", r["definition"]))
    if len({f.flag_id for f in flags}) != len(flags):
        raise ValueError("hazard_flags.csv has a repeated flag_id")
    return flags


def load_required_details() -> list[RequiredDetail]:
    return [RequiredDetail(r["id"], r["label"]) for r in _rows("required_details.csv")]


def load_checklists() -> dict[str, list[str]]:
    by_type: dict[str, list[tuple[int, str]]] = {}
    for r in _rows("checklists.csv"):
        by_type.setdefault(r["type_id"], []).append((int(r["position"]), r["item"]))
    return {t: [item for _, item in sorted(items)] for t, items in by_type.items()}


def load_instruction_phrases() -> list[str]:
    return [r["phrase"].lower() for r in _rows("instruction_phrases.csv") if r["phrase"]]


@dataclass(frozen=True)
class Reference:
    """All the visible tables, loaded once."""
    scale: dict[int, str]                 # severity level -> name
    scale_rows: list[SeverityLevel]
    types: list[IncidentType]
    type_names: dict[str, str]
    hazard_flags: dict[str, HazardFlag]   # flag id -> flag
    details: dict[str, str]               # detail id -> plain label
    checklists: dict[str, list[str]]
    instruction_phrases: list[str]


def load_reference() -> Reference:
    scale_rows = load_severity_scale()
    types = load_incident_types()
    return Reference(
        scale={s.level: s.name for s in scale_rows},
        scale_rows=scale_rows,
        types=types,
        type_names={t.id: t.name for t in types},
        hazard_flags={f.flag_id: f for f in load_hazard_flags()},
        details={d.id: d.label for d in load_required_details()},
        checklists=load_checklists(),
        instruction_phrases=load_instruction_phrases(),
    )
