# Reference tables

**ILLUSTRATIVE ASSUMPTIONS.** Everything in this folder is an example made up for this demonstration. It is not company policy and it is not regulation.

| File | What it holds |
|---|---|
| `severity_scale.csv` | The four severity levels (1 Low to 4 Critical) and what each means. |
| `incident_types.csv` | The nine incident types the reader can choose from. |
| `hazard_flags.csv` | The fixed list of things the AI reader can flag, such as "someone was hurt". Each flag has a minimum severity (a "floor"). The code checks the list and can only raise a severity to that minimum, never lower it. The AI reader is told this list and its minimums, so its rating should already match; the code is a confirmation. The `definition` column is the wording given to the AI reader. A flag marked `needs_person` (text aimed at the reader) sends the report to the top for a person to read. The plain-language label for each flag is in `triage/text.py`. |
| `required_details.csv` | The seven details a complete report should contain. |
| `checklists.csv` | A short generic reviewer checklist for each incident type. It is not instructions. |
| `instruction_phrases.csv` | Phrases that look like instructions aimed at the reader. A report containing one is sent to the top for a person to read, because the AI reader's answer for it cannot be trusted. |
