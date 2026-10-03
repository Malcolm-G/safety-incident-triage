# Safety Incident Triage

**Status: PLANNED.** The sorting rules, the review queue, the reviewer panel and the quality checks exist and are tested, but they run on hand-written example answers. The AI reader is not connected yet. This label changes to "prototype" only once the whole thing runs end to end.

This app is meant to sort free-text incident reports from an aircraft ground-handling operation into a review queue, so a safety officer can read the most urgent first. A person confirms everything. Nothing is sent or closed.

## Illustrative only
**ILLUSTRATIVE ASSUMPTIONS.** The severity scale, the keyword list and the checklists are examples made up for this demonstration. They are not company policy or regulation. Items would be flagged for review against your own company's policy.

## What exists so far
- Twenty invented reports, all marked **SYNTHETIC** (see `data/README.md`).
- A review queue, worked out by fixed rules, with the most urgent first and the reasons in plain words.
- A report card that keeps three things apart: what the AI reader suggested, the review priority set by the rules, and the reviewer's decision.
- A reviewer panel. Lowering a severity needs a written reason. A decision never replaces the computed result.
- A chart of reports by review priority, and four quality checks.

## Not built yet
The AI reader itself, saved answers for a demo without a key, the accuracy check, and live mode.

## Run
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
pytest
```
