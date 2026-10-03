# Safety Incident Triage

**Status: PLANNED.** Only the first stage exists: invented reports, example reference tables and a page that lists them. The reading, sorting and review features are not built yet.

This app is meant to sort free-text incident reports from an aircraft ground-handling operation into a review queue, so a safety officer can read the most urgent first. A person confirms everything. Nothing is sent or closed.

## Illustrative only
**ILLUSTRATIVE ASSUMPTIONS.** The severity scale, the keyword list and the checklists are examples made up for this demonstration. They are not company policy or regulation. Items would be flagged for review against your own company's policy.

## Data
All reports are **SYNTHETIC**: invented people, flights and places. See `data/README.md`.

## Run
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
pytest
```
