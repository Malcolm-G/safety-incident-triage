"""Drawing helpers. Every sentence comes from triage/text.py."""
import re

import pandas as pd
import streamlit as st

from triage import reviewer, text
from triage.checks import Check
from triage.loader import Report
from triage.models import Triage
from triage.reference import Reference
from triage.reviewer import DecisionError, DecisionLog

_MD_SPECIAL = re.compile(r"([\\`*_{}\[\]()#+\-.!|<>~$&:])")


def md_escape(value) -> str:
    """st.table renders cell text as Markdown. Report text is untrusted, so show it literally:
    no links, images, bold or HTML can come from a report."""
    return _MD_SPECIAL.sub(r"\\\1", str(value if value is not None else ""))


# ---------- small helpers ----------

def priority_label(t: Triage) -> str:
    return text.BAND_NEEDS_PERSON if t.failed else text.BAND_NAMES[t.final_severity]


def ai_label(t: Triage, ref: Reference) -> str:
    return ref.scale[t.suggested_severity] if t.suggested_severity else text.AI_NO_ANSWER


def details_label(t: Triage) -> str:
    return text.DETAILS_INCOMPLETE.format(n=t.missing_count or 1) if t.incomplete else text.DETAILS_COMPLETE


def reviewer_label(log: DecisionLog, report_id: str, ref: Reference) -> str:
    d = log.latest(report_id)
    return reviewer.describe(d, ref.scale) if d else text.STATUS_WAITING


def why_label(t: Triage) -> str:
    parts = [t.reasons[0]]
    if t.disagree:
        parts.append(text.FLAG_DISAGREE)
    if t.instruction_like:
        parts.append(text.FLAG_INSTRUCTION)
    return " | ".join(parts)


# ---------- page parts ----------

def render_check_summary(checks: list[Check]) -> None:
    failed = [c for c in checks if not c.passed]
    if failed:
        st.error(text.CHECKS_FAILED.format(names="; ".join(c.name for c in failed)))
    else:
        st.success(text.CHECKS_ALL_PASSED.format(n=len(checks)))
    with st.expander(text.CHECKS_HEADING):
        for c in checks:
            st.write(f"{text.CHECK_PASSED if c.passed else text.CHECK_FAILED}: {c.name}. {c.detail}")
        st.caption(text.CHECKS_NOTE)


def render_queue(queue: list[Triage], log: DecisionLog, ref: Reference) -> None:
    st.subheader(text.QUEUE_HEADING)
    st.caption(text.QUEUE_INTRO)
    st.table(pd.DataFrame([{
        text.COL_ORDER: i,
        text.COL_REPORT: md_escape(t.report_id),
        text.COL_PRIORITY: md_escape(priority_label(t)),
        text.COL_AI: md_escape(ai_label(t, ref)),
        text.COL_WHY: md_escape(why_label(t)),
        text.COL_DETAILS: md_escape(details_label(t)),
        text.COL_REVIEWER: md_escape(reviewer_label(log, t.report_id, ref)),
    } for i, t in enumerate(queue, start=1)]).set_index(text.COL_ORDER), alt=text.ALT_QUEUE)


def _save_decision(triage: Triage) -> None:
    """Button callback: record a decision next to the computed result. Never edits the result."""
    rid = triage.report_id
    action = {text.ACTION_CONFIRM: reviewer.CONFIRM, text.ACTION_CHANGE: reviewer.CHANGE,
              text.ACTION_NEEDS_INFO: reviewer.NEEDS_INFO}.get(st.session_state.get(f"action_{rid}"))
    try:
        decision = reviewer.decide(triage, st.session_state.get("reviewer_name", ""), action or "",
                                   st.session_state.get(f"severity_{rid}"),
                                   st.session_state.get(f"reason_{rid}", ""))
    except DecisionError as e:
        st.session_state["review_message"] = ("error", rid, str(e))
        return
    st.session_state["decisions"].add(decision)
    st.session_state["review_message"] = ("ok", rid, text.SAVED_OK)
    st.session_state[f"reason_{rid}"] = ""


def render_reviewer(t: Triage, log: DecisionLog, ref: Reference) -> None:
    rid = t.report_id
    st.markdown(f"**{text.REVIEWER_HEADING}**")
    st.caption(text.REVIEWER_INTRO)
    st.text_input(text.NAME_LABEL, key="reviewer_name")
    action = st.radio(text.ACTION_LABEL, text.ACTIONS, key=f"action_{rid}")
    st.selectbox(text.SEVERITY_LABEL, [1, 2, 3, 4], index=t.final_severity - 1, key=f"severity_{rid}",
                 format_func=lambda n: f"{ref.scale[n]} ({n})", disabled=action != text.ACTION_CHANGE)
    st.text_area(text.REASON_LABEL, key=f"reason_{rid}")
    st.button(text.SAVE_BUTTON, key=f"save_{rid}", type="primary", on_click=_save_decision, args=(t,))
    message = st.session_state.get("review_message")
    if message and message[1] == rid:
        (st.error if message[0] == "error" else st.success)(message[2])


def render_card(t: Triage, report: Report, log: DecisionLog, ref: Reference) -> None:
    c_ai, c_rules, c_rev = st.columns(3)
    with c_ai:
        st.markdown(f"**{text.CARD_AI_HEADING}**")
        if t.reading:
            r = t.reading
            st.write(f"{text.CARD_LOOKS_LIKE}: {ref.type_names[r.incident_type]}")
            st.write(f"{text.CARD_SEVERITY}: {ref.scale[r.suggested_severity]} ({r.suggested_severity})")
            st.write(f"{text.CARD_HURT} {text.YES_NO[r.injury_mentioned]}")
            st.write(f"{text.CARD_DAMAGE} {text.YES_NO[r.damage_mentioned]}")
            st.text(f"{text.CARD_SUMMARY}: {r.summary}")
        else:
            st.write(text.NO_ANSWER_CARD)
    with c_rules:
        st.markdown(f"**{text.CARD_RULES_HEADING}**")
        st.write(f"{priority_label(t)} ({t.final_severity})")
        for reason in t.reasons:
            st.text(reason)
    with c_rev:
        st.markdown(f"**{text.CARD_REVIEWER_HEADING}**")
        latest = log.latest(t.report_id)
        st.write(reviewer.describe(latest, ref.scale) if latest else text.NO_DECISION)
        earlier = log.history(t.report_id)[:-1]
        if earlier:
            st.caption(text.HISTORY_HEADING)
            for d in reversed(earlier):
                st.text(reviewer.describe(d, ref.scale))

    st.markdown(f"**{text.MISSING_HEADING}**")
    if t.missing:
        for m in t.missing:
            st.text(ref.details.get(m, m))
    else:
        st.text(text.NOTHING_MISSING)
    st.markdown(f"**{text.CHECKLIST_HEADING}**")
    for item in t.checklist:
        st.text(item)
    st.markdown(f"**{text.REPORT_TEXT_HEADING}**")
    st.text(report.text)
    render_reviewer(t, log, ref)


def render_all(queue: list[Triage], log: DecisionLog, ref: Reference) -> None:
    st.subheader(text.CHART_HEADING)
    counts = {text.BAND_NAMES[n]: 0 for n in (1, 2, 3, 4)}
    for t in queue:
        counts[text.BAND_NAMES[t.final_severity]] += 1
    st.bar_chart(pd.DataFrame({text.CHART_COUNT: counts}), sort=False, alt=text.CHART_ALT, y_label=text.CHART_COUNT)
    st.subheader(text.ALL_HEADING)
    st.table(pd.DataFrame([{
        text.COL_REPORT: md_escape(t.report_id),
        text.COL_TYPE: md_escape(ref.type_names[t.reading.incident_type] if t.reading else text.AI_NO_ANSWER),
        text.COL_AI: md_escape(ai_label(t, ref)),
        text.COL_PRIORITY: md_escape(priority_label(t)),
        text.COL_STATUS: md_escape(log.status(t.report_id)),
    } for t in sorted(queue, key=lambda x: x.report_id)]).set_index(text.COL_REPORT), alt=text.ALT_ALL)


def render_scale(ref: Reference) -> None:
    st.markdown(f"**{text.SEVERITY_HEADING}**")
    st.table(pd.DataFrame([{
        text.COLUMN_LEVEL: s.level, text.COLUMN_NAME: s.name, text.COLUMN_MEANING: s.meaning,
    } for s in ref.scale_rows]).set_index(text.COLUMN_LEVEL), alt=text.ALT_SCALE)
    st.markdown(f"**{text.TYPES_HEADING}**")
    st.table(pd.DataFrame([{
        text.COLUMN_NAME: t.name, text.COLUMN_DESCRIPTION: t.description,
    } for t in ref.types]).set_index(text.COLUMN_NAME), alt=text.ALT_TYPES)
