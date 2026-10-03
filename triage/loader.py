"""Reads the reports exactly as written. Nothing else: the expected answers are kept apart and the app never opens them."""
import csv
import json
from dataclasses import dataclass
from pathlib import Path

import config


class DatasetMissing(Exception):
    """The chosen dataset folder or its reports file is not there."""


@dataclass(frozen=True)
class Report:
    report_id: str
    submitted_on: str
    text: str


@dataclass(frozen=True)
class DatasetInfo:
    name: str
    label: str


def _folder(name: str | None) -> Path:
    folder = config.dataset_dir(name or config.DATASET)
    if not folder.exists():
        raise DatasetMissing(f"Dataset folder not found: data/{folder.name}/")
    return folder


def load_info(name: str | None = None) -> DatasetInfo:
    folder = _folder(name)
    meta = json.loads((folder / "dataset.json").read_text(encoding="utf-8"))
    return DatasetInfo(name=meta["name"], label=meta["label"])


def load_reports(name: str | None = None) -> list[Report]:
    path = _folder(name) / "reports.csv"
    if not path.exists():
        raise DatasetMissing("reports.csv not found")
    with path.open(newline="", encoding="utf-8-sig") as f:
        return [Report(r["report_id"].strip(), r["submitted_on"].strip(), r["report_text"].strip())
                for r in csv.DictReader(f)]
