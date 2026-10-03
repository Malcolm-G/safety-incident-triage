"""Every sentence the app shows to a person lives here, in plain language for a safety officer.

Keeping them in one file lets a test check the wording of everything the app says about itself.
(Report text is not here: it belongs to the reports, not to the app.)
"""

# ---------- page-level ----------
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
FIXTURE_BANNER = ("HAND-WRITTEN EXAMPLE ANSWERS. The AI reader's answers on this page were written by hand "
                  "for development. They are not real AI output.")
DATA_MISSING = "The reports could not be found. Set DATASET=synthetic to use the built-in examples."

TAB_QUEUE = "Review queue"
TAB_ALL = "All reports and chart"
TAB_ABOUT = "About the scale"

# ---------- scale and reports (from the first stage) ----------
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
ALT_REPORTS = "The invented incident reports"
ALT_SCALE = "The illustrative severity scale"
ALT_TYPES = "The incident types"

# ---------- queue ----------
BAND_NAMES = {4: "Read now", 3: "High", 2: "Medium", 1: "Low"}
BAND_NEEDS_PERSON = "Read now: needs a person"
QUEUE_HEADING = "Review queue"
QUEUE_INTRO = "Most urgent first. The order is worked out by fixed rules, not by the AI reader."
COL_ORDER = "Order"
COL_REPORT = "Report"
COL_PRIORITY = "Review priority"
COL_AI = "AI suggested"
COL_WHY = "Why it is here"
COL_DETAILS = "Details"
COL_REVIEWER = "Reviewer"
COL_TYPE = "Looks like"
COL_STATUS = "Status"
AI_NO_ANSWER = "No answer"
DETAILS_COMPLETE = "Complete"
DETAILS_INCOMPLETE = "Incomplete: {n} missing"
ALT_QUEUE = "The review queue, most urgent first"

# ---------- report card ----------
OPEN_REPORT_LABEL = "Open a report"
CARD_AI_HEADING = "What the AI reader suggested"
CARD_RULES_HEADING = "Review priority (set by the rules)"
CARD_REVIEWER_HEADING = "Reviewer's decision"
CARD_LOOKS_LIKE = "Looks like"
CARD_SEVERITY = "Suggested severity"
CARD_HURT = "Anyone hurt?"
CARD_DAMAGE = "Anything damaged?"
CARD_SUMMARY = "In one sentence"
YES_NO = {"yes": "Yes", "no": "No", "unclear": "Unclear"}
MISSING_HEADING = "What is missing"
NOTHING_MISSING = "The AI reader did not mark anything as missing."
CHECKLIST_HEADING = "Generic reviewer checklist, not instructions"
REPORT_TEXT_HEADING = "The report"
NO_ANSWER_CARD = "There is no usable answer from the AI reader for this report."

# ---------- reasons the rules give (plain words) ----------
REASON_AGREE = "The AI reader's suggestion stands: {severity}."
REASON_RAISED = ("The AI reader suggested {suggested}. The rules raised it to {final} "
                 "because the report mentions {words}.")
REASON_INJURY_CONFLICT = ("The text contains words that suggest a serious injury, but the AI reader says "
                          "nobody was hurt. Please check.")
REASON_DAMAGE_CONFLICT = ("The text contains words about damage to an aircraft, but the AI reader says nothing "
                          "was damaged. Please check.")
REASON_INSTRUCTION = ("This report contains text that looks like instructions to the reader. "
                      "It was ignored. Please read it yourself.")
REASON_SHORT = "This is a very short report, so details are likely missing."
REASON_MISSING = "Details marked as missing: {items}."
FAILURE_REASONS = {
    "invalid_answer": "The AI reader's answer could not be used, so a person should read this report now.",
    "wrong_report": "The AI reader's answer was for a different report, so a person should read this one now.",
    "timed_out": "The AI reader took too long, so a person should read this report now.",
    "refused": "The AI reader did not give an answer, so a person should read this report now.",
    "service_error": "The AI reader could not be reached, so a person should read this report now.",
    "no_saved_answer": "There is no saved answer for this report, so a person should read it now.",
}
FLAG_DISAGREE = "The rules and the AI reader disagree"
FLAG_INSTRUCTION = "Contains instruction-like text"

# ---------- quality checks ----------
CHECKS_HEADING = "Quality checks"
CHECKS_ALL_PASSED = "All {n} quality checks passed."
CHECKS_FAILED = "A quality check failed, so please do not rely on this queue: {names}."
CHECK_COUNT_NAME = "Every report is in the queue"
CHECK_COUNT_DETAIL = "{reports} reports in, {queued} in the queue."
CHECK_PRIORITY_NAME = "Every report has a review priority"
CHECK_PRIORITY_DETAIL = "{bad} report(s) without a valid priority."
CHECK_ORDER_NAME = "The queue is in priority order"
CHECK_ORDER_DETAIL = "{bad} place(s) where the order is wrong."
CHECK_STATUS_NAME = "Every report has a status"
CHECK_STATUS_DETAIL = "{bad} report(s) without a status."
CHECK_PASSED = "Passed"
CHECK_FAILED = "Failed"
CHECKS_NOTE ="These checks catch mistakes in how the page is put together. They cannot tell whether a judgment is right."

# ---------- all reports and chart ----------
ALL_HEADING = "All reports"
CHART_HEADING = "Reports by review priority"
CHART_ALT = "A bar chart counting reports at each review priority"
CHART_COUNT = "Reports"
ALT_ALL = "All reports with the AI suggestion, the review priority and the status"

# ---------- reviewer ----------
REVIEWER_HEADING = "Reviewer panel"
REVIEWER_INTRO = ("Your decision is recorded next to the computed result. It never replaces it. "
                  "Decisions are kept only while this page is open.")
NAME_LABEL = "Your name"
ACTION_LABEL = "What would you like to do?"
ACTION_CONFIRM = "Confirm the review priority"
ACTION_CHANGE = "Change the severity"
ACTION_NEEDS_INFO = "I need more information"
ACTIONS = (ACTION_CONFIRM, ACTION_CHANGE, ACTION_NEEDS_INFO)
SEVERITY_LABEL = "Severity to record"
REASON_LABEL = "Reason (needed if you lower the severity)"
SAVE_BUTTON = "Save decision"
SAVED_OK = "Decision saved for this session."
ERR_NAME = "Please enter your name."
ERR_REASON = "Please write a reason of at least 5 characters before lowering a severity."
ERR_SAME = "That is the same as the review priority. Choose \"Confirm\" instead, or pick a different severity."
ERR_SEVERITY = "Please choose a severity from 1 to 4."
STATUS_WAITING = "Waiting for a reviewer"
STATUS_CONFIRMED = "Confirmed"
STATUS_RAISED = "Raised"
STATUS_OVERRULED = "Overruled"
STATUS_NEEDS_INFO = "Needs more information"
DECISION_CONFIRMED = "Confirmed by {name} ({time})"
DECISION_RAISED = "Raised to {severity} by {name} ({time})"
DECISION_OVERRULED = "Overruled by {name}: {reason} ({time})"
DECISION_NEEDS_INFO = "{name} needs more information ({time})"
HISTORY_HEADING = "Earlier decisions"
NO_DECISION = "No decision yet."
