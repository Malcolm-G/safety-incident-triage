"""Answer labels for the accuracy check. ONLY the accuracy script and the tests may use this.

The app never imports this file, and the labels are never shown to a user. A test enforces both.
"""
import csv
from dataclasses import dataclass

import config


@dataclass(frozen=True)
class Label:
    report_id: str
    split: str              # "tuning" or "holdout"
    expected_type: str
    alt_type: str | None    # another type that is also acceptable, if the report is truly ambiguous
    severity_min: int
    severity_max: int
    notes: str


def load_labels(dataset: str | None = None) -> list[Label]:
    path = config.dataset_dir(dataset or config.DATASET) / "labels.csv"
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [Label(r["report_id"].strip(), r["split"].strip(), r["expected_type"].strip(),
                      r["alt_type"].strip() or None, int(r["severity_min"]), int(r["severity_max"]),
                      r["notes"].strip())
                for r in csv.DictReader(f)]
