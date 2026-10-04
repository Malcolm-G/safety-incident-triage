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
from views import (open_report, render_all, render_check_summary, render_panel, render_queue,
                    render_scale)

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
use_saved = config.ANSWERS == "saved" and (config.dataset_dir() / "ai_answers.json").exists()
st.warning(text.CACHED_BANNER if use_saved else text.FIXTURE_BANNER)

ref = load_reference()
reports_by_id = {r.report_id: r for r in reports}
outcomes = load_fixture_outcomes([r.report_id for r in reports],
                                 filename="ai_answers.json" if use_saved else "extractions_fixture.json")
queue = build_queue(reports, outcomes, ref)

log = st.session_state.setdefault("decisions", DecisionLog())
statuses = {r.report_id: log.status(r.report_id) for r in reports}
render_check_summary(run_checks(reports, queue, statuses))

# Tracked tabs keep the open tab when the page reruns (for example while typing a name).
tab_queue, tab_all, tab_about = st.tabs([text.TAB_QUEUE, text.TAB_ALL, text.TAB_ABOUT],
                                        key="main_tabs", on_change="rerun")
with tab_queue:
    # The first report is open when the page loads. With no report open, the queue uses the full width.
    open_id = st.session_state.setdefault("open_id", queue[0].report_id)
    if open_id not in reports_by_id:
        open_id = None
    if open_id is not None:
        left, right = st.columns([5, 3])
    else:
        left, right = st.container(), None
    with left:
        clicked = render_queue(queue, log, ref, open_id)
    if clicked is not None and clicked != open_id:     # a different row was clicked
        open_report(clicked)
        st.rerun()
    if open_id is not None and right is not None:
        with right:
            render_panel(next(t for t in queue if t.report_id == open_id), reports_by_id[open_id], log, ref)
with tab_all:
    render_all(queue, log, ref)
with tab_about:
    render_scale(ref)
