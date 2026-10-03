# Reference tables

**ILLUSTRATIVE ASSUMPTIONS.** Everything in this folder is an example made up for this demonstration. It is not company policy and it is not regulation.

| File | What it holds |
|---|---|
| `severity_scale.csv` | The four severity levels (1 Low to 4 Critical) and what each means. |
| `incident_types.csv` | The nine incident types the reader can choose from. |
| `keyword_table.csv` | Words and phrases the code looks for. Each group sets a minimum severity (a "floor"). The code can only raise a report's priority with these, never lower it. |
| `required_details.csv` | The seven details a complete report should contain. |
| `checklists.csv` | A short generic reviewer checklist for each incident type. It is not instructions. |
| `instruction_phrases.csv` | Phrases that look like instructions aimed at the reader. They add a flag for a person. They never change a priority. |

Keyword matching is simple text matching. It can over-trigger (for example "no injuries" contains "injur"). Over-raising is accepted here. Under-raising is not.
