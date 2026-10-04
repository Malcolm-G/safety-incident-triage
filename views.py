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
    return text.BAND_NEEDS_PERSON if t.needs_person else text.BAND_NAMES[t.final_severity]


def ai_label(t: Triage, ref: Reference) -> str:
    return ref.scale[t.suggested_severity] if t.suggested_severity else text.AI_NO_ANSWER


def details_label(t: Triage) -> str:
    return text.DETAILS_INCOMPLETE.format(n=t.missing_count or 1) if t.incomplete else text.DETAILS_COMPLETE


def reviewer_label(log: DecisionLog, report_id: str, ref: Reference) -> str:
    d = log.latest(report_id)
    return reviewer.describe(d, ref.scale) if d else text.STATUS_WAITING


def why_label(t: Triage) -> str:
    """The clear reasons, for example 'Someone was hurt: a loader hurt her hand'. Nothing about who decided what."""
    return " | ".join(t.why)


def clicked_report_id(cells: list, ids: list[str]) -> str | None:
    """Turn the table's selected cell into the report id of its row. Accepts [row, column], (row, column) or
    {"row": ..., "column": ...}. None if nothing valid is selected."""
    if not cells:
        return None
    first = cells[0]
    row = first.get("row") if isinstance(first, dict) else (first[0] if isinstance(first, (list, tuple)) and first else first)
    try:
        position = int(row)
    except (TypeError, ValueError):
        return None
    return ids[position] if 0 <= position < len(ids) else None


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


def queue_frame(queue: list[Triage], log: DecisionLog, ref: Reference, open_id: str | None):
    """The queue as a table, with the open report's row shaded. st.dataframe shows cells as plain text,
    so report text cannot become a link."""
    frame = pd.DataFrame([{
        text.COL_ORDER: i,
        text.COL_REPORT: t.report_id,
        text.COL_PRIORITY: priority_label(t),
        text.COL_WHY: why_label(t),
        text.COL_DETAILS: details_label(t),
        text.COL_REVIEWER: reviewer_label(log, t.report_id, ref),
    } for i, t in enumerate(queue, start=1)])
    shade = [t.report_id == open_id for t in queue]
    return frame.style.apply(
        lambda row: ["background-color:rgba(255,75,75,.18)" if shade[row.name] else "" for _ in row], axis=1)


def render_queue(queue: list[Triage], log: DecisionLog, ref: Reference, open_id: str | None) -> str | None:
    """Draw the queue. Clicking any cell in a row selects that row's report. Returns the clicked report id, or None."""
    st.subheader(text.QUEUE_HEADING)
    st.caption(text.QUEUE_INTRO)
    ids = [t.report_id for t in queue]
    event = st.dataframe(
        queue_frame(queue, log, ref, open_id), hide_index=True, height="content", on_select="rerun",
        selection_mode="single-cell", key=f"queue_{st.session_state.get('queue_gen', 0)}",
        alt=text.ALT_QUEUE_TABLE,
        column_config={
            text.COL_ORDER: st.column_config.NumberColumn(width="small"),
            text.COL_REPORT: st.column_config.TextColumn(width="small"),
            text.COL_PRIORITY: st.column_config.TextColumn(width="medium"),
            text.COL_WHY: st.column_config.TextColumn(width="large"),
            text.COL_DETAILS: st.column_config.TextColumn(width="medium"),
            text.COL_REVIEWER: st.column_config.TextColumn(width="medium"),
        },
    )
    return clicked_report_id(list(event.selection.cells), ids)


def open_report(report_id: str | None) -> None:
    """Open a report in the panel (or close the panel with None). Closing clears the table's selection
    by changing its key, so the next click is a fresh one."""
    st.session_state["open_id"] = report_id
    if report_id is None:
        st.session_state["queue_gen"] = st.session_state.get("queue_gen", 0) + 1


def _close_panel() -> None:
    open_report(None)


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


def _box(title: str):
    """A bordered section with a plain heading. Use as: with _box(title): ..."""
    box = st.container(border=True)
    box.markdown(f"**{title}**")
    return box


def render_panel(t: Triage, report: Report, log: DecisionLog, ref: Reference) -> None:
    """The report, in its own bordered boxes, in reading order."""
    with st.container(border=True):
        head, close = st.columns([4, 1])
        head.subheader(t.report_id)
        close.button(text.CLOSE_BUTTON, key="close_panel", on_click=_close_panel)
        kind = ref.type_names[t.reading.incident_type] if t.reading else text.AI_NO_ANSWER
        st.write(f"{priority_label(t)} ({t.final_severity}). {text.LOOKS_LIKE}: {kind}")

    with _box(text.SECTION_REPORT):
        st.text(report.text)

    with _box(text.SECTION_WHY):
        for line in t.why:
            st.text(line)
        if t.raised:
            st.text(text.RAISED_NOTE.format(suggested=ref.scale[t.suggested_severity], final=ref.scale[t.final_severity]))
        for note in t.notes:
            st.text(note)

    with _box(text.SECTION_AI):
        if t.reading:
            r = t.reading
            st.text(f"{text.CARD_RATING}: {ref.scale[r.suggested_severity]} ({r.suggested_severity})")
            st.text(f"{text.CARD_REASON_GIVEN}: {r.rating_reason}")
            found = [text.WHY_LINE.format(label=text.FLAG_LABELS[f.flag], detail=f.detail) for f in r.hazard_flags]
            st.text(f"{text.CARD_FOUND}: " + ("; ".join(found) if found else text.NOTHING_FOUND))
            st.text(f"{text.CARD_SUMMARY}: {r.summary}")
        else:
            st.text(text.NO_ANSWER_CARD)

    with _box(text.SECTION_MISSING):
        if t.missing:
            for m in t.missing:
                st.text(ref.details.get(m, m))
        else:
            st.text(text.NOTHING_MISSING)

    with _box(text.SECTION_CHECKLIST):
        for item in t.checklist:
            st.text(item)

    with _box(text.SECTION_DECISION):
        latest = log.latest(t.report_id)
        st.text(reviewer.describe(latest, ref.scale) if latest else text.NO_DECISION)
        earlier = log.history(t.report_id)[:-1]
        if earlier:
            st.caption(text.HISTORY_HEADING)
            for d in reversed(earlier):
                st.text(reviewer.describe(d, ref.scale))
        st.divider()
        st.markdown(f"**{text.REVIEWER_HEADING}**")
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
