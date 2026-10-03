"""Streamlit entry point. Thin: loads data and draws it."""
import streamlit as st

import config
from triage import text
from triage.loader import DatasetMissing, load_info, load_reports
from triage.reference import load_incident_types, load_severity_scale
from views import render_reports, render_scale

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
render_scale(load_severity_scale(), load_incident_types())
render_reports(reports)
