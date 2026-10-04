"""The accuracy runner's grading, on the hand-written answers (no network)."""
import json

import config
from evaluate import grade
from triage.fixtures import outcome_from_json
from triage.labels import load_labels
from triage.models import Failure


def rows():
    items = json.loads((config.DATASET_DIR / "extractions_fixture.json").read_text(encoding="utf-8")) if hasattr(config, "DATASET_DIR") else \
        json.loads((config.dataset_dir() / "extractions_fixture.json").read_text(encoding="utf-8"))
    return [{"report_id": i["report_id"], "repeat": 1, "answer": i} for i in items]


def test_grading_counts_failures_apart_and_never_as_wrong(reports, ref):
    labels = [l for l in load_labels() if l.split == "holdout"]
    got = grade([r for r in rows() if r["report_id"] in {l.report_id for l in labels}], labels, reports, ref)
    assert got["failed (not scored)"] == 1 and got["UNDER-triage (target 0)"] == 0


def test_a_missing_or_bad_saved_answer_becomes_a_failure():
    assert outcome_from_json({"failure": "timed_out"}) is Failure.timed_out
    assert outcome_from_json({"failure": "nonsense"}) is Failure.invalid_answer
    assert outcome_from_json({"report_id": "x"}) is Failure.invalid_answer
