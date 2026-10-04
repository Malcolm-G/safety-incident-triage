"""Streamlit entry point. Thin: loads data, runs the rules, draws the page."""
import os

import streamlit as st

import config
from triage import text
from triage import live
from triage.checks import run_checks
from triage.fixtures import load_fixture_outcomes
from triage.loader import DatasetMissing, load_reports
from triage.priority import build_queue
from triage.reference import load_reference
from triage.reviewer import DecisionLog
from views import (open_report, render_all, render_check_problem, render_key, render_live, render_queue,
                    render_report_page, render_scale, render_tally)

config.load_dotenv()
try:                                    # hosted copies keep the key and passcode in the host's secrets
    for _name in ("ANTHROPIC_API_KEY", "LIVE_PASSCODE"):
        if _name in st.secrets:
            os.environ.setdefault(_name, str(st.secrets[_name]))
except Exception:
    pass
st.set_page_config(page_title=text.APP_TITLE, layout="wide")
st.title(text.APP_TITLE)

try:
    reports = load_reports()
except DatasetMissing:
    st.error(text.DATA_MISSING)
    st.stop()

use_saved = config.ANSWERS == "saved" and (config.dataset_dir() / "ai_answers.json").exists()
ref = load_reference()
reports_by_id = {r.report_id: r for r in reports}
outcomes = load_fixture_outcomes([r.report_id for r in reports],
                                 filename="ai_answers.json" if use_saved else "extractions_fixture.json")
queue = build_queue(reports, outcomes, ref)

log = st.session_state.setdefault("decisions", DecisionLog())
statuses = {r.report_id: log.status(r.report_id) for r in reports}
render_check_problem(run_checks(reports, queue, statuses))

# A report is open: it takes over the page, until the Back button is pressed.
open_id = st.session_state.setdefault("open_id", None)
if open_id in reports_by_id:
    render_report_page(next(t for t in queue if t.report_id == open_id), reports_by_id[open_id], log, ref)
    st.stop()

st.write(text.TAGLINE)
st.caption(text.NOTHING_SENT + " " + text.REVIEW_AGAINST_POLICY)
st.info("\n\n".join([text.NOTICE_INVENTED, text.NOTICE_SAVED if use_saved else text.NOTICE_HAND, text.NOTICE_EXAMPLES]))
render_key()

# Tracked tabs keep the open tab when the page reruns.
names = [text.TAB_QUEUE, text.TAB_ALL, text.TAB_ABOUT] + ([text.TAB_LIVE] if live.enabled() else [])
tab_queue, tab_all, tab_about, *tab_live = st.tabs(names, key="main_tabs", on_change="rerun")
with tab_queue:
    render_tally(queue, log, ref)
    clicked = render_queue(queue, log, ref)
    if clicked is not None:
        open_report(clicked)
        st.rerun()
with tab_all:
    render_all(queue, log, ref)
with tab_about:
    render_scale(ref)
if tab_live:
    with tab_live[0]:
        render_live(ref)
