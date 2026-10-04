"""Accuracy runner. Reads the AI on the reports, grades by code against labels.csv.

  python evaluate.py --tag r1                  # tuning reports only, 3 repeats each
  python evaluate.py --tag final --final       # all reports; hold-out numbers are aggregate only and every look is logged

Results are written as they finish and a rerun with the same --tag resumes. Report text is never printed.
"""
import argparse
import json
import random
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import config
from triage import reader
from triage.fixtures import outcome_from_json
from triage.models import Failure
from triage.labels import load_labels
from triage.loader import load_reports
from triage.priority import triage_report
from triage.reference import load_reference

OUT = config.ROOT / "scratch" / "evals"
PRICE = {"sonnet": (2, 10), "haiku": (1, 5), "opus": (4, 20), "fable": (10, 50)}    # dollars per million tokens
RETRIES, WORKERS = 2, 4


def run_one(client, report, ref, model, repeat):
    for attempt in range(RETRIES + 1):
        res = reader.read_report(client, report, ref, model)
        if res.outcome not in (Failure.timed_out, Failure.service_error):
            break
        time.sleep(random.uniform(1, 3) * (attempt + 1))
    o = res.outcome
    return {"report_id": report.report_id, "repeat": repeat, "model_used": res.model_used,
            "in": res.input_tokens, "out": res.output_tokens,
            "answer": o.model_dump() if hasattr(o, "model_dump") else {"failure": o.value}}


def grade(rows, labels, reports, ref):
    """Closed-set, code-graded numbers for one set of rows."""
    by_label, by_report = {l.report_id: l for l in labels}, {r.report_id: r for r in reports}
    n = failed = type_ok = rating_ok = final_ok = under = over = read_now = 0
    for row in rows:
        lab = by_label[row["report_id"]]
        o = outcome_from_json(row["answer"])
        t = triage_report(by_report[row["report_id"]], o, ref)
        n += 1
        read_now += t.final_severity == 4
        under += t.final_severity < lab.severity_min
        over += t.final_severity > lab.severity_max
        final_ok += lab.severity_min <= t.final_severity <= lab.severity_max
        if t.failed:
            failed += 1
            continue
        type_ok += t.reading.incident_type in (lab.expected_type, lab.alt_type)
        rating_ok += lab.severity_min <= t.reading.suggested_severity <= lab.severity_max
    scored = n - failed
    return {"answers": n, "failed (not scored)": failed, "type correct": f"{type_ok}/{scored}",
            "rating in range": f"{rating_ok}/{scored}", "final priority in range": f"{final_ok}/{n}",
            "UNDER-triage (target 0)": under, "over-raise": over, "in Read now": f"{read_now}/{n}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", required=True)
    ap.add_argument("--model", default=config.MODEL)
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--final", action="store_true", help="include the hold-out reports (aggregate only, logged)")
    a = ap.parse_args()

    ref, reports, labels = load_reference(), load_reports(), load_labels()
    labels = [l for l in labels if a.final or l.split == "tuning"]
    ids = {l.report_id for l in labels}
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / f"{a.tag}.jsonl"
    rows = [json.loads(x) for x in path.read_text(encoding="utf-8").splitlines()] if path.exists() else []
    done = {(r["report_id"], r["repeat"]) for r in rows}
    jobs = [(r, k) for k in range(1, a.repeats + 1) for r in reports if r.report_id in ids and (r.report_id, k) not in done]

    if jobs:
        client = reader.make_client()
        with ThreadPoolExecutor(WORKERS) as pool, path.open("a", encoding="utf-8") as f:
            for row in pool.map(lambda j: run_one(client, j[0], ref, a.model, j[1]), jobs):
                f.write(json.dumps(row) + "\n"); f.flush(); rows.append(row)

    bad_model = sum(bool(r["model_used"]) and not r["model_used"].startswith(a.model) for r in rows)
    rate = next((v for k, v in PRICE.items() if k in a.model), (0, 0))
    cost = sum(r["in"] * rate[0] + r["out"] * rate[1] for r in rows) / 1e6
    print(f"model {a.model} | {len(rows)} answers | cost about ${cost:.3f} | model-name mismatches: {bad_model}")

    for split in ("tuning", "holdout"):
        part = [l for l in labels if l.split == split]
        if not part:
            continue
        if split == "holdout":
            (OUT / "holdout_looks.log").open("a").write(f"{datetime.now(timezone.utc).isoformat()} {a.tag} {a.model}\n")
        print(f"\n{split} ({'aggregate only' if split == 'holdout' else 'per repeat'})")
        for k in ([None] if split == "holdout" else range(1, a.repeats + 1)):
            sub = [r for r in rows if r["report_id"] in {l.report_id for l in part} and (k is None or r["repeat"] == k)]
            print(f"  repeat {k or 'all'}: ", grade(sub, part, reports, ref))
        if split == "tuning":                       # the out-of-range cases, by id only
            for r in rows:
                lab = next((l for l in part if l.report_id == r["report_id"]), None)
                if lab is None:
                    continue
                t = triage_report(next(x for x in reports if x.report_id == lab.report_id), outcome_from_json(r["answer"]), ref)
                if not lab.severity_min <= t.final_severity <= lab.severity_max:
                    print(f"  OUT OF RANGE {lab.report_id} repeat {r['repeat']}: final {t.final_severity}, expected {lab.severity_min}-{lab.severity_max}")


if __name__ == "__main__":
    main()
