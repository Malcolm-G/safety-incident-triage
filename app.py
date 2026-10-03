"""Streamlit entry point. Thin: loads data, runs the rules, draws the page."""
import streamlit as st

import config
from triage import text
from triage.checks import run_checks
from triage.fixtures import load_fixture_outcomes
from triage.loader import DatasetMissing, load_info, load_reports
from triage.priority import build_queue
from triage.reference import load_reference
from triage.reviewer import DecisionLog
from views import (render_all, render_card, render_check_summary, render_queue, render_scale)

config.load_dotenv()
st.set_page_config(page_title=text.APP_TITLE, layout="wide")
st.title(text.APP_TITLE)
st.write(text.TAGLINE)
st.caption(text.NOTHING_SENT + " " + text.REVIEW_AGAINST_POLICY)

try:
    info = load_info()
    reports = load_reports()
except DatasetMissing:
    st.error(text.DATA_MISSING)
    st.stop()

st.warning(info.label)
st.info(text.ILLUSTRATIVE_NOTE)
st.warning(text.FIXTURE_BANNER)

ref = load_reference()
reports_by_id = {r.report_id: r for r in reports}
outcomes = load_fixture_outcomes([r.report_id for r in reports])
queue = build_queue(reports, outcomes, ref)

log = st.session_state.setdefault("decisions", DecisionLog())
statuses = {r.report_id: log.status(r.report_id) for r in reports}
render_check_summary(run_checks(reports, queue, statuses))

# Tracked tabs keep the open tab when the page reruns (for example while typing a name).
tab_queue, tab_all, tab_about = st.tabs([text.TAB_QUEUE, text.TAB_ALL, text.TAB_ABOUT],
                                        key="main_tabs", on_change="rerun")
with tab_queue:
    render_queue(queue, log, ref)
    open_id = st.selectbox(text.OPEN_REPORT_LABEL, [t.report_id for t in queue], key="open_report")
    chosen = next(t for t in queue if t.report_id == open_id)
    render_card(chosen, reports_by_id[open_id], log, ref)
with tab_all:
    render_all(queue, log, ref)
with tab_about:
    render_scale(ref)
