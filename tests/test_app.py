"""The page: a clickable queue, the report panel on the right in separate boxes, the reviewer panel, and the checks."""
import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

import config
from triage import text
from views import clicked_report_id


def fresh_app(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("DATASET", "synthetic")
    return AppTest.from_file(str(config.ROOT / "app.py"))


@pytest.fixture
def at(monkeypatch):
    return fresh_app(monkeypatch).run(timeout=60)


def queue_rows(app):
    return app.dataframe[0].value


def click_row(app, position):
    """Simulate clicking a cell in a row of the queue, as the browser would (a cell is [row, column name])."""
    key = f"queue_{app.session_state['queue_gen'] if 'queue_gen' in app.session_state else 0}"
    cells = [[position, text.COL_WHY]] if position is not None else []
    app.session_state[key] = {"selection": {"rows": [], "columns": [], "cells": cells}}
    return app.run(timeout=60)


def opened_report(app):
    shown = [s.value for s in app.subheader if s.value.startswith("SYN-")]
    return shown[0] if shown else None


# ---- the page ----

def test_page_shows_banners_checks_and_the_nothing_sent_line(at):
    assert not at.exception
    assert [t.value for t in at.title] == [text.APP_TITLE]
    assert any(w.value.startswith("SYNTHETIC DATA") for w in at.warning)
    assert any(w.value.startswith("HAND-WRITTEN EXAMPLE ANSWERS") for w in at.warning)
    assert any(i.value.startswith("ILLUSTRATIVE ASSUMPTIONS") for i in at.info)
    assert any(text.NOTHING_SENT in c.value for c in at.caption)
    assert any(s.value == text.CHECKS_ALL_PASSED.format(n=4) for s in at.success)


def test_the_queue_is_a_clickable_table_of_all_reports_failure_first(at):
    rows = queue_rows(at)
    assert len(rows) == 28
    assert list(rows.columns) == [text.COL_ORDER, text.COL_REPORT, text.COL_PRIORITY, text.COL_WHY,
                                  text.COL_DETAILS, text.COL_REVIEWER]
    assert rows.iloc[0][text.COL_REPORT] == "SYN-026"
    assert rows.iloc[0][text.COL_PRIORITY] == text.BAND_NEEDS_PERSON


def test_why_it_is_here_gives_a_clear_reason_with_a_little_detail_not_a_story(at):
    why = {r[text.COL_REPORT]: r[text.COL_WHY] for _, r in queue_rows(at).iterrows()}
    assert why["SYN-002"] == "Someone was hurt: a loader hurt his lower back lifting a heavy bag"
    assert why["SYN-016"] == ("Serious injury: a ramp agent's wrist was badly hurt and an ambulance took him away"
                              " | Someone was hurt: he tripped over a strap and landed on his hand")
    assert why["SYN-004"] == "Fuel leak or spill: a few litres dripped from a hose coupling during refuelling"
    assert why["SYN-001"] == ("Aircraft damaged: a dent and a scrape near the cargo door"
                              " | Aircraft hit by a vehicle or equipment: a baggage tractor reversed into the aircraft")
    assert why["SYN-006"] == text.FAILURE_REASONS["timed_out"]
    assert why["SYN-014"] == text.REASON_INSTRUCTION
    for report_id, line in why.items():
        for narration in ("AI reader suggested", "Its own answers", "raised it", "disagree", "the rules"):
            assert narration not in line, (report_id, line)


# ---- click a row: the report opens in a panel ----

def test_the_first_report_is_open_when_the_page_loads(at):
    assert opened_report(at) == "SYN-026"
    assert at.session_state["open_id"] == "SYN-026"


def test_the_panel_has_its_sections_in_reading_order_each_in_a_box(at):
    order = [m.value.strip("*") for m in at.markdown]
    wanted = [text.SECTION_REPORT, text.SECTION_WHY, text.SECTION_AI, text.SECTION_MISSING,
              text.SECTION_CHECKLIST, text.SECTION_DECISION, text.REVIEWER_HEADING]
    positions = [order.index(w) for w in wanted]
    assert positions == sorted(positions)
    import re
    views_source = (config.ROOT / "views.py").read_text(encoding="utf-8")
    assert len(re.findall(r"container\(border=True\)", views_source)) >= 2 and "def _box(" in views_source


def test_clicking_another_row_opens_that_report(at):
    at = click_row(at, 3)
    assert not at.exception
    assert opened_report(at) == "SYN-016"
    assert any("badly hurt his wrist" in t.value for t in at.text)
    assert any("Serious injury: a ramp agent's wrist" in t.value for t in at.text)


def test_the_panel_shows_every_detail_of_the_reason_and_what_the_AI_said(at):
    at = click_row(at, 7)                                 # SYN-002
    assert opened_report(at) == "SYN-002"
    texts = [t.value for t in at.text]
    assert "Someone was hurt: a loader hurt his lower back lifting a heavy bag" in texts
    assert text.RAISED_NOTE.format(suggested="Low", final="High") in texts
    assert any(t.startswith(f"{text.CARD_REASON_GIVEN}: The writer calls it a minor strain.") for t in texts)


def test_clicking_any_cell_of_a_row_opens_it(at):
    for column in (text.COL_ORDER, text.COL_REPORT, text.COL_PRIORITY, text.COL_DETAILS, text.COL_REVIEWER):
        key = "queue_0"
        at.session_state[key] = {"selection": {"rows": [], "columns": [], "cells": [[5, column]]}}
        at.run(timeout=60)
        assert not at.exception
        assert opened_report(at) == list(queue_rows(at)[text.COL_REPORT])[5], column


def test_the_open_row_is_shaded(at):
    from views import queue_frame
    assert at.dataframe[0].value.iloc[0][text.COL_REPORT] == "SYN-026"
    import views, inspect
    assert "background-color" in inspect.getsource(views.queue_frame)


def test_the_close_button_hides_the_panel_and_clears_the_selection(at):
    at.button(key="close_panel").click()
    at.run(timeout=60)
    assert not at.exception
    assert opened_report(at) is None
    assert at.session_state["open_id"] is None and at.session_state["queue_gen"] == 1
    assert not [b for b in at.button if b.label == text.CLOSE_BUTTON]
    assert len(queue_rows(at)) == 28                      # the queue is still there, now with no row selected
    at.run(timeout=60)                                    # a further run changes nothing: no loop
    assert opened_report(at) is None and not at.exception
    at = click_row(at, 4)                                 # clicking a row opens the panel again
    assert opened_report(at) is not None and at.session_state["open_id"] is not None


def test_clicking_the_open_row_again_does_not_loop(at):
    at = click_row(at, 0)
    assert not at.exception and opened_report(at) == "SYN-026"


def test_clicked_report_id_helper():
    ids = ["A", "B", "C"]
    assert clicked_report_id([], ids) is None
    assert clicked_report_id([[0, "Why"]], ids) == "A"
    assert clicked_report_id([(2, "Why")], ids) == "C"
    assert clicked_report_id([{"row": 1, "column": "Why"}], ids) == "B"
    assert clicked_report_id([[np.int64(1), "Why"]], ids) == "B"
    assert clicked_report_id([[3, "Why"]], ids) is None   # a stale selection
    assert clicked_report_id([[-1, "Why"]], ids) is None
    assert clicked_report_id([["x", "Why"]], ids) is None
    assert clicked_report_id([[None, "Why"]], ids) is None


def test_the_all_reports_table_and_chart_are_there(at):
    assert len(at.get("vega_lite_chart")) >= 1
    assert len(at.table[0].value) == 28


def test_tabs_are_tracked_so_a_rerun_keeps_the_open_tab(at):
    assert "main_tabs" in at.session_state


# ---- reviewer flow, now inside the panel ----

def fill(app, name, action, severity=None, reason="", report="SYN-026"):
    app.text_input(key="reviewer_name").set_value(name)
    app.radio(key=f"action_{report}").set_value(action).run(timeout=60)   # the severity box unlocks after this
    if severity is not None:
        app.selectbox(key=f"severity_{report}").set_value(severity)
    app.text_area(key=f"reason_{report}").set_value(reason)


def test_lowering_without_a_reason_is_refused_and_nothing_is_saved(at):
    before = queue_rows(at).copy()
    fill(at, "Sam Lee", text.ACTION_CHANGE, severity=2, reason="")
    at.button(key="save_SYN-026").click()
    at.run(timeout=60)
    assert any(text.ERR_REASON in e.value for e in at.error)
    assert len(at.session_state["decisions"]) == 0
    assert queue_rows(at).iloc[0][text.COL_REVIEWER] == text.STATUS_WAITING
    assert queue_rows(at).equals(before)


def test_a_lowered_item_stays_visible_as_overruled_the_queue_does_not_move_and_the_panel_stays_open(at):
    order_before = list(queue_rows(at)[text.COL_REPORT])
    priority_before = list(queue_rows(at)[text.COL_PRIORITY])
    fill(at, "Sam Lee", text.ACTION_CHANGE, severity=2, reason="Checked with the lead, it was a harmless item.")
    at.button(key="save_SYN-026").click()
    at.run(timeout=60)
    assert not at.exception and not at.error
    assert any(text.SAVED_OK in s.value for s in at.success)
    rows = queue_rows(at)
    assert "Overruled by Sam Lee: Checked with the lead" in rows.iloc[0][text.COL_REVIEWER]
    assert list(rows[text.COL_REPORT]) == order_before and list(rows[text.COL_PRIORITY]) == priority_before
    assert opened_report(at) == "SYN-026"                               # saving does not close the panel
    assert any("Overruled by Sam Lee" in t.value for t in at.text)      # shown in the decision box too


def test_confirming_needs_a_name(at):
    fill(at, "", text.ACTION_CONFIRM)
    at.button(key="save_SYN-026").click()
    at.run(timeout=60)
    assert any(text.ERR_NAME in e.value for e in at.error)


def test_confirming_is_saved_without_a_reason(at):
    fill(at, "Sam Lee", text.ACTION_CONFIRM)
    at.button(key="save_SYN-026").click()
    at.run(timeout=60)
    assert not at.error
    assert "Confirmed by Sam Lee" in queue_rows(at).iloc[0][text.COL_REVIEWER]


def test_a_failed_check_shows_one_plain_message(monkeypatch):
    from triage import checks as checks_module
    monkeypatch.setattr(checks_module, "run_checks",
                        lambda reports, queue, statuses: [checks_module.Check(text.CHECK_COUNT_NAME, False, "x")])
    app = fresh_app(monkeypatch).run(timeout=60)
    assert any(e.value.startswith("A quality check failed") for e in app.error)


def test_report_text_is_shown_literally_never_as_a_link(monkeypatch):
    from views import md_escape
    out = md_escape("![x](http://a.example/p.png) **bold** <b>hi</b> [a](http://b.example)")
    assert "http://" not in out and "<b>" not in out and "\\*\\*bold\\*\\*" in out


def test_missing_dataset_gives_a_plain_message(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("DATASET", "does_not_exist")
    monkeypatch.setattr(config, "DATASET", "does_not_exist")
    app = AppTest.from_file(str(config.ROOT / "app.py")).run(timeout=60)
    assert not app.exception
    assert any(text.DATA_MISSING in e.value for e in app.error)
