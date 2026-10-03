# Reference tables

**ILLUSTRATIVE ASSUMPTIONS.** Everything in this folder is an example made up for this demonstration. It is not company policy and it is not regulation.

| File | What it holds |
|---|---|
| `severity_scale.csv` | The four severity levels (1 Low to 4 Critical) and what each means. |
| `incident_types.csv` | The nine incident types the reader can choose from. |
| `consistency_rules.csv` | A check on the AI reader's OWN answers. Each row says: if the reader's answer to a field has this value, the severity should be at least this high (a "floor"). The code can only raise a severity with these, never lower it. It does not read the report text, so wording such as "nobody was hurt" cannot cause a false alarm. The plain-language reason for each rule is in `triage/text.py`. |
| `required_details.csv` | The seven details a complete report should contain. |
| `checklists.csv` | A short generic reviewer checklist for each incident type. It is not instructions. |
| `instruction_phrases.csv` | Phrases that look like instructions aimed at the reader. A report containing one is sent to the top for a person to read, because the AI reader's answer for it cannot be trusted. |
