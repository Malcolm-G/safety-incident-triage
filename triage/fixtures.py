"""Hand-written example answers for the AI reader (stage P1). NOT real AI output.

Read from data/<dataset>/extractions_fixture.json. An entry is either a reading or {"report_id": ..., "failure": ...}.
An entry that does not fit the fixed fields becomes a failure, exactly as a bad real answer would.
"""
import json

import config
from pydantic import ValidationError

from triage.models import Failure, IncidentReading, Outcome


def outcome_from_json(item: dict) -> Outcome:
    """A saved answer (a reading, or {"failure": ...}) back into an Outcome. A bad one is a failure."""
    try:
        return Failure(item["failure"]) if "failure" in item else IncidentReading.model_validate(item)
    except (ValueError, ValidationError):
        return Failure.invalid_answer


def load_fixture_outcomes(report_ids: list[str], dataset: str | None = None,
                          filename: str = "extractions_fixture.json") -> dict[str, Outcome]:
    path = config.dataset_dir(dataset or config.DATASET) / filename
    items = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    out: dict[str, Outcome] = {}
    for item in items:
        rid = item.get("report_id") if isinstance(item, dict) else None
        if not isinstance(rid, str):
            continue
        if "failure" in item:
            try:
                out[rid] = Failure(item["failure"])
            except ValueError:
                out[rid] = Failure.invalid_answer
            continue
        try:
            out[rid] = IncidentReading.model_validate(item)
        except ValidationError:
            out[rid] = Failure.invalid_answer
    for rid in report_ids:
        out.setdefault(rid, Failure.no_saved_answer)
    return out
