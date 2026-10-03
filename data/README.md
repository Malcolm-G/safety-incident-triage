# Data

## data/synthetic/
**SYNTHETIC.** Twenty incident reports written for this demonstration. The people, flights, places and events are all invented. They are not based on any real incident.

| File | What it holds |
|---|---|
| `reports.csv` | The 20 invented reports. This is all the app shows. |
| `labels.csv` | The expected answers for the accuracy check: the incident type and an acceptable severity range for each report, split into 12 "tuning" and 8 "hold-out" reports. The app never reads this file and never shows it. These are illustrative judgments, not expert safety judgments. |
| `dataset.json` | The name and the banner text for this data set. |

## data/reference/
Illustrative example tables. See the README in that folder.
