"""Drawing helpers. Every sentence comes from triage/text.py."""
import re

import pandas as pd
import streamlit as st

from triage import text
from triage.loader import Report
from triage.reference import IncidentType, SeverityLevel

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$&:])")


def md_escape(value) -> str:
    """st.table renders cell text as Markdown. Report text is untrusted, so show it literally:
    no links, images, bold or HTML can come from a report."""
    return _MD_SPECIAL.sub(r"\\\1", str(value if value is not None else ""))


def render_reports(reports: list[Report]) -> None:
    st.subheader(text.REPORTS_HEADING)
    st.caption(text.REPORTS_INTRO)
    st.table(pd.DataFrame([{
        text.COLUMN_ID: md_escape(r.report_id),
        text.COLUMN_DATE: md_escape(r.submitted_on),
        text.COLUMN_TEXT: md_escape(r.text),
    } for r in reports]).set_index(text.COLUMN_ID), alt="The invented incident reports")


def render_scale(scale: list[SeverityLevel], types: list[IncidentType]) -> None:
    with st.expander(text.ABOUT_SCALE_HEADING):
        st.markdown(f"**{text.SEVERITY_HEADING}**")
        st.table(pd.DataFrame([{
            text.COLUMN_LEVEL: s.level, text.COLUMN_NAME: s.name, text.COLUMN_MEANING: s.meaning,
        } for s in scale]).set_index(text.COLUMN_LEVEL), alt="The illustrative severity scale")
        st.markdown(f"**{text.TYPES_HEADING}**")
        st.table(pd.DataFrame([{
            text.COLUMN_NAME: t.name, text.COLUMN_DESCRIPTION: t.description,
        } for t in types]).set_index(text.COLUMN_NAME), alt="The incident types")
