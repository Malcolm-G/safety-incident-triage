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
class Keyword:
    group: str
    keyword: str
    floor: int
    reason: str


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


def load_keywords() -> list[Keyword]:
    out = [Keyword(r["group"], r["keyword"].lower(), _level(r["floor"], "keyword_table.csv"), r["reason"])
           for r in _rows("keyword_table.csv")]
    if any(not k.keyword for k in out):
        raise ValueError("keyword_table.csv has an empty keyword")
    return out


def load_required_details() -> list[RequiredDetail]:
    return [RequiredDetail(r["id"], r["label"]) for r in _rows("required_details.csv")]


def load_checklists() -> dict[str, list[str]]:
    by_type: dict[str, list[tuple[int, str]]] = {}
    for r in _rows("checklists.csv"):
        by_type.setdefault(r["type_id"], []).append((int(r["position"]), r["item"]))
    return {t: [item for _, item in sorted(items)] for t, items in by_type.items()}


def load_instruction_phrases() -> list[str]:
    return [r["phrase"].lower() for r in _rows("instruction_phrases.csv") if r["phrase"]]
