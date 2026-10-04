# Safety Incident Triage

**Status: PROTOTYPE (demo of saved results).** An AI reader has read all 28 invented reports once and its answers are saved, so the demo runs without a key. Live mode (typing in a new report) is off unless a passcode is set.

This app sorts free-text incident reports from an aircraft ground-handling operation into a review queue, so a safety officer can read the most urgent first. A person confirms everything. Nothing is sent or closed.

Right now it is a **test stage**: reviewers check whether the AI reader rated each report sensibly, and what they find is used to improve the AI reader's instructions before it ranks real reports for officers to deal with. The page has a short key explaining each column.

## Illustrative only
**ILLUSTRATIVE ASSUMPTIONS.** The severity scale, the fixed list of flags and the checklists are examples made up for this demonstration. They are not company policy or regulation. Items would be flagged for review against your own company's policy.

## What it does
- 28 invented reports, all marked **SYNTHETIC** (see `data/README.md`).
- A review queue, most urgent first, with the reason in plain words.
- Click any row and the full report opens in a panel beside it, in separate boxes. A Close button gives the table the full width again.
- The report card keeps three things apart: what the AI reader suggested, the review priority worked out by fixed rules, and the reviewer's decision.
- A reviewer panel. Lowering a priority needs a written reason. A decision never replaces the computed result, and a lowered item stays visible as "Overruled by NAME: REASON".
- A tally of reviewer decisions and a download of them as a CSV file. The page opens with the queue only; clicking a row opens its report.
- A chart of reports by review priority. Four quality checks run quietly in the background and show a plain message only if one fails.

## Where it would fit in a company
A sensible first phase: reviewers read the queue and check whether each report was rated appropriately. Every confirm or change is evidence on whether the AI reader's instructions and the fixed rules work, before anyone relies on the queue. Reviewers stay in charge throughout. In this demo, decisions are kept only while the page is open. A tally above the queue shows how many were confirmed, raised or lowered, and a button downloads every decision as a CSV file, so a team can compare reviewers' decisions with the computed priority.

## Live mode (optional)
If the host sets a passcode, an "Add a report" tab appears. After the passcode, a person can pick a sample or paste an invented report and the AI reader reads it now. The tab says: "Do not enter real incident details or personal information. Reports are not saved."
- Limits: 2000 characters per report, 5 reports per visit, 100 a day for the whole app, and 5 wrong passcode tries per visit.
- The typed text goes only to the reader. It is cleared from the page as soon as it is read, and it is not written to a file, a log or an error message. A test checks this. The result stays on screen until you leave the page or press Clear.
- The result is not added to the queue. Nothing is sent or closed.
- This is a simple gate for a demo, not strong security.

## Results of the accuracy check
The expected answers were written down before the AI reader saw any report. Prompt and model were chosen on the 20 tuning reports only, then everything was frozen and run once over all 28 reports, three times each. The saved demo answers are the first of those three.

| Measure | Tuning (20 reports) | Hold-out (8 reports, 3 runs each) |
|---|---|---|
| Answers with no usable result | 0 | 0 |
| Incident type correct | 19/20 | 24/24 |
| AI rating inside the expected range | 19/20 | 19/24 |
| Final priority inside the expected range | 19/20 | 19/24 |
| **Under-triage (final priority below the expected range)** | **0** | **2 of 24 answers** |
| Over-raise (final priority above the range) | 1 | 3 of 24 answers |
| Placed in "Read now" | 5/20 | 3/24 |

What to take from this:
- Tuning looked almost perfect and the hold-out did not. The hold-out found 2 under-triaged answers. That is the number that matters most for a safety tool, and it shows the fixed list and the AI reader together are not enough on their own. A person must read the queue.
- The hold-out was looked at once, as totals only. The individual hold-out cases were not opened and nothing was changed after seeing the result.
- The one tuning over-raise (SYN-026) is by design: a report with text aimed at the reader always goes to the top for a person, even when the incident itself is harmless. Its expected rating range (1 to 2) conflicts with that rule, so it counts against the AI on purpose.
- One tuning type miss (SYN-027, a stair truck rolling onto a foot): the AI called it an equipment fault. The priority was still Critical.
- Cost of the whole tuning and final work was under $2.

## Limits of this test
- The hold-out is **not fully independent**. The same builder wrote the reports and the expected answers, and had seen the hold-out text.
- The expected answers are illustrative judgments, not expert safety judgments.
- 28 invented reports is a small test. Counts are coarse: one report is about 4 percentage points.
- Three runs of each report gave the same scores on the tuning set, so run-to-run noise looked small there. It was not measured on every hold-out report separately.
- Prompt-injection protection is reduced, not removed. It rests on the reader being told to treat the report as data, a flag for text aimed at the reader, and the fixed rules.
- The fixed list can over-raise. For example a mild ache marked "someone was hurt" is raised to High.
- The passcode is a shared word, and the daily cap counts only while the app stays running.
- The four quality checks catch mistakes in how the page is put together. They cannot tell whether a judgment is right.
- Anthropic's docs list Claude Haiku 4.5 as retiring not sooner than 15 October 2026, so Claude Sonnet 5.5 was used.

## Why there are no keyword rules
An early version looked for words such as "fire" and "injury" in each report and raised the priority when it found one. That went wrong. A report saying "No fire, no injuries" was pushed to Critical, because plain word matching cannot understand "no". So the keyword rules were removed.

## How it works
- **The AI reader** (Claude Sonnet 5.5) gets one report and the instructions in `triage/prompt.py`, which are built from the same reference tables the code checks. It must return a fixed set of fields (JSON checked against a schema): incident type, a rating from 1 to 4, a one-sentence reason, flags from a fixed list each with a short detail, missing details, and a one-sentence summary. It has no field for advice or actions.
- **The code** (`triage/priority.py`) reads only the flag ids, never the detail text. It can only raise a rating to the minimum for a flag. It cannot lower one.
- **Fail up:** any failure (timeout, service error, refusal, bad or wrong-report answer) or text aimed at the reader sends the report to "Needs a person now" at the top.
- **A person** confirms, changes or asks for more information. The decision is recorded next to the computed result.
- **Evaluation** (`evaluate.py`): runs concurrently, saves each result as it finishes, retries with a random wait, records the model name and cost, and grades by code against `labels.csv`. Hold-out numbers are totals only, behind `--final`, and every look is logged.
- **Report text is untrusted.** It is never used as instructions and is shown as plain text.

## Run
```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
pytest
```
For live mode set `ANTHROPIC_API_KEY` and `LIVE_PASSCODE` in the host's secrets (or a local `.env`). To run the accuracy check you need an API key in the environment (a local `.env` file is ignored by git): `python evaluate.py --tag NAME`.
