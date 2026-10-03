# Safety Incident Triage

**Status: PLANNED.** The sorting rules, the review queue, the reviewer panel and the quality checks exist and are tested, but they run on hand-written example answers. The AI reader is not connected yet. This label changes to "prototype" only once the whole thing runs end to end.

This app is meant to sort free-text incident reports from an aircraft ground-handling operation into a review queue, so a safety officer can read the most urgent first. A person confirms everything. Nothing is sent or closed.

## Illustrative only
**ILLUSTRATIVE ASSUMPTIONS.** The severity scale, the fixed list of flags and the checklists are examples made up for this demonstration. They are not company policy or regulation. Items would be flagged for review against your own company's policy.

## What exists so far
- Twenty invented reports, all marked **SYNTHETIC** (see `data/README.md`).
- A review queue, worked out by fixed rules, with the most urgent first and the reasons in plain words.
- A report card that keeps three things apart: what the AI reader suggested, the review priority set by the rules, and the reviewer's decision.
- A reviewer panel. Lowering a severity needs a written reason. A decision never replaces the computed result.
- A chart of reports by review priority, and four quality checks.

## Why there are no keyword rules
An early version looked for words such as "fire" and "injury" in each report and raised the priority when it found one. That went wrong. A report saying "No fire, no injuries" was pushed to Critical, because plain word matching cannot understand "no". So the keyword rules were removed.

Now the AI reader reads the report. It gives a rating, a one-sentence reason, and a list of flags from a fixed list (for example "someone was hurt"). The reader is told that list and the minimum severity for each flag, so its rating should already match. The code then only confirms: if a flag's minimum is higher than the rating, the code raises the rating to it. The code can only raise a severity, never lower it, and it does not read the report's wording. A report whose text tries to give the reader instructions goes to the top for a person to read, because the reader's answer for it cannot be trusted. The same happens when the reader gives no usable answer.

## Not built yet
The AI reader itself, saved answers for a demo without a key, the accuracy check, and live mode.

## Known limits so far
- The checks on the reader's answers can over-raise. For example, a mild ache that the reader marks as "someone was hurt" is raised to High.
- All data is invented and small, and the example answers are written by hand.
- The four quality checks catch mistakes in how the page is put together. They cannot tell whether a judgment is right.

## Run
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
pytest
```
