"""Loads the visible reference tables in data/reference/. All of them are illustrative examples.

Each loader checks its file and refuses to continue on a bad row, so a typo in a table
cannot quietly weaken a rule.
"""
import csv
from dataclasses import dataclass

import config

LEVELS = (1, 2, 3, 4)

# The AI reader's answers a consistency rule may look at, and the values each can take.
RULE_FIELDS = {
    "injury_mentioned": {"yes", "no", "unclear"},
    "damage_mentioned": {"yes", "no", "unclear"},
}


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
class ConsistencyRule:
    """If the AI reader's answer for `field` equals `value`, the severity must be at least `floor`."""
    rule_id: str
    field: str
    value: str
    floor: int


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


def load_consistency_rules() -> list[ConsistencyRule]:
    type_ids = {t.id for t in load_incident_types()}
    rules = []
    for r in _rows("consistency_rules.csv"):
        where = f"consistency_rules.csv ({r['rule_id']})"
        floor = _level(r["floor"], where)
        field, value = r["field"], r["value"]
        if field == "incident_type":
            if value not in type_ids:
                raise ValueError(f"{where}: unknown incident type {value!r}")
        elif field in RULE_FIELDS:
            if value not in RULE_FIELDS[field]:
                raise ValueError(f"{where}: {value!r} is not a possible answer for {field}")
        else:
            raise ValueError(f"{where}: rules can only look at the reader's fixed answers, not {field!r}")
        rules.append(ConsistencyRule(r["rule_id"], field, value, floor))
    if len({r.rule_id for r in rules}) != len(rules):
        raise ValueError("consistency_rules.csv has a repeated rule_id")
    return rules


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
    consistency: list[ConsistencyRule]
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
        consistency=load_consistency_rules(),
        details={d.id: d.label for d in load_required_details()},
        checklists=load_checklists(),
        instruction_phrases=load_instruction_phrases(),
    )
