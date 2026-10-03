"""Every sentence the app shows to a person lives here, in plain language for a safety officer.

Keeping them in one file lets a test check the wording of everything the app says about itself.
(Report text is not here: it belongs to the reports, not to the app.)
"""

APP_TITLE = "Safety incident triage"
TAGLINE = ("This page sorts incident reports so a safety officer can read the most urgent first. "
           "A person confirms everything.")

# The one sentence about what the app never does. It is allowed by exact match in the wording test.
NOTHING_SENT = "Nothing is sent or closed."
ALLOWED_SENTENCES = (NOTHING_SENT,)

SYNTHETIC_BANNER = "SYNTHETIC DATA. Every report here is invented for demonstration. Nothing is real."
ILLUSTRATIVE_NOTE = ("ILLUSTRATIVE ASSUMPTIONS. The severity scale, the keyword list and the checklists "
                     "in this app are examples. They are not company policy or regulation.")
REVIEW_AGAINST_POLICY = "Items are flagged for review against your own company's policy."

REPORTS_HEADING = "Reports"
REPORTS_INTRO = "These are the invented reports this demonstration works on."
ABOUT_SCALE_HEADING = "About the scale"
SEVERITY_HEADING = "Severity scale"
TYPES_HEADING = "Incident types"
COLUMN_ID = "Report"
COLUMN_DATE = "Date"
COLUMN_TEXT = "What the report says"
COLUMN_LEVEL = "Level"
COLUMN_NAME = "Name"
COLUMN_MEANING = "What it means"
COLUMN_DESCRIPTION = "What it covers"

DATA_MISSING = "The reports could not be found. Set DATASET=synthetic to use the built-in examples."
