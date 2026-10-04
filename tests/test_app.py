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
    monkeypatch.setattr(config, "ANSWERS", "fixture")      # the tests below rely on the hand-written answers
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

def test_page_shows_one_plain_notice_and_the_nothing_sent_line(at):
    assert not at.exception
    assert [x.value for x in at.title] == [text.APP_TITLE]
    assert not at.warning and not at.success and not at.error     # no stack of banners, no quality-check boxes
    assert len(at.info) == 1
    notice = at.info[0].value
    for sentence in (text.NOTICE_INVENTED, text.NOTICE_HAND, text.NOTICE_EXAMPLES):
        assert sentence in notice
    assert any(text.NOTHING_SENT in c.value for c in at.caption)


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

def test_no_report_is_open_when_the_page_loads_and_a_note_says_to_click(at):
    assert opened_report(at) is None and at.session_state["open_id"] is None
    assert any(c.value == text.PANEL_HINT for c in at.caption)
    assert not [b for b in at.button if b.label == text.CLOSE_BUTTON]


def row_of(app, report_id):
    return list(queue_rows(app)[text.COL_REPORT]).index(report_id)


def test_the_panel_has_its_sections_in_reading_order_each_in_a_box(at):
    at = click_row(at, row_of(at, "SYN-011"))             # a report with details missing
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
    assert any(f"{text.CARD_REASON_GIVEN}: The writer calls it a minor strain." in t for t in texts)
    assert not any(t.startswith("What it found") for t in texts)          # the flags are shown once, under why it is here


def test_clicking_any_cell_of_a_row_opens_it(at):
    for column in (text.COL_ORDER, text.COL_REPORT, text.COL_PRIORITY, text.COL_DETAILS, text.COL_REVIEWER):
        key = "queue_0"
        at.session_state[key] = {"selection": {"rows": [], "columns": [], "cells": [[5, column]]}}
        at.run(timeout=60)
        assert not at.exception
        assert opened_report(at) == list(queue_rows(at)[text.COL_REPORT])[5], column


def test_the_open_row_is_shaded(at):
    at = click_row(at, 0)
    assert at.session_state["open_id"] == "SYN-026"
    import views, inspect
    assert "background-color" in inspect.getsource(views.queue_frame)


def test_the_close_button_hides_the_panel_and_clears_the_selection(at):
    at = click_row(at, 0)
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
    at = click_row(at, 0)                                 # open the first report
    before = queue_rows(at).copy()
    fill(at, "Sam Lee", text.ACTION_CHANGE, severity=2, reason="")
    at.button(key="save_SYN-026").click()
    at.run(timeout=60)
    assert any(text.ERR_REASON in e.value for e in at.error)
    assert len(at.session_state["decisions"]) == 0
    assert queue_rows(at).iloc[0][text.COL_REVIEWER] == text.STATUS_WAITING
    assert queue_rows(at).equals(before)


def test_a_lowered_item_stays_visible_as_overruled_the_queue_does_not_move_and_the_panel_stays_open(at):
    at = click_row(at, 0)                                 # open the first report
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
    at = click_row(at, 0)                                 # open the first report
    fill(at, "", text.ACTION_CONFIRM)
    at.button(key="save_SYN-026").click()
    at.run(timeout=60)
    assert any(text.ERR_NAME in e.value for e in at.error)


def test_confirming_is_saved_without_a_reason(at):
    at = click_row(at, 0)                                 # open the first report
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
    assert [e.value for e in app.error] == [text.CHECKS_FAILED]
    assert "technical" not in text.CHECKS_FAILED


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


# ---- saved answers from the real final run ----

def test_the_page_shows_the_cached_results_banner_and_no_failures_from_saved_answers(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("DATASET", "synthetic")
    app = AppTest.from_file(str(config.ROOT / "app.py")).run(timeout=60)
    assert not app.exception
    assert text.NOTICE_SAVED in app.info[0].value and text.NOTICE_HAND not in app.info[0].value
    assert len(queue_rows(app)) == 28
    assert not app.error


def test_every_saved_answer_is_valid_and_covers_every_report(reports):
    from triage.fixtures import load_fixture_outcomes
    from triage.models import Failure
    got = load_fixture_outcomes([r.report_id for r in reports], filename="ai_answers.json")
    assert len(got) == 28 and not any(isinstance(v, Failure) for v in got.values())


def test_a_sample_report_can_be_dropped_into_the_live_box(monkeypatch):
    from tests.test_live import live_app
    app = live_app(monkeypatch)
    app.text_input(key="live_code").set_value("open-sesame")
    [b for b in app.button if b.label == text.LIVE_UNLOCK][0].click()
    app.run(timeout=60)
    app.selectbox(key="live_sample").select("Understated: just a scratch")
    [b for b in app.button if b.label == text.LIVE_SAMPLE_USE][0].click()
    app.run(timeout=60)
    assert app.text_area(key="live_text").value == text.LIVE_SAMPLES["Understated: just a scratch"]


# ---- nothing repeated in the panel ----

def panel_texts(app):
    return [x.value for x in app.text]


def test_a_report_with_no_flag_shows_its_reason_once_and_no_empty_missing_box(at):
    at = click_row(at, row_of(at, "SYN-007"))             # nothing found, nothing missing, short report
    texts = panel_texts(at)
    assert text.NO_FLAGS_NOTE in texts
    reason = "A belt loader stopped working; nobody was hurt and nothing was damaged."
    assert sum(reason in x for x in texts) == 1                           # the reason appears once, in the AI box
    assert not any(x.startswith(text.CARD_SUMMARY) for x in texts)        # short report: no summary
    assert text.SECTION_MISSING not in [m.value.strip("*") for m in at.markdown]


def test_a_long_report_gets_its_summary_and_missing_details_are_one_line(at):
    at = click_row(at, row_of(at, "SYN-027"))
    assert any(x.startswith(text.CARD_SUMMARY) for x in panel_texts(at))
    at = click_row(at, row_of(at, "SYN-023"))
    assert "Whether anyone was hurt; What was done straight away" in panel_texts(at)


def test_the_ai_rating_is_shown_only_when_it_differs_from_the_review_priority(at):
    at = click_row(at, row_of(at, "SYN-002"))             # AI said Low, the fixed list raised it
    assert any(x.startswith(f"{text.CARD_RATING}: Low (1). ") for x in panel_texts(at))
    at = click_row(at, row_of(at, "SYN-016"))             # AI and review priority agree
    assert not any(x.startswith(f"{text.CARD_RATING}:") for x in panel_texts(at))


# ---- tally and decisions file ----

def test_the_tally_starts_at_zero_and_the_download_waits_for_a_decision(at):
    assert any(c.value.startswith("Reviewed 0 of 28:") and text.KEEP_NOTE in c.value for c in at.caption)
    button = at.get("download_button")[0]
    assert button.proto.disabled is True


def test_saving_a_decision_updates_the_tally_and_enables_the_download(at):
    at = click_row(at, 0)
    fill(at, "Sam Lee", text.ACTION_CONFIRM)
    at.button(key="save_SYN-026").click()
    at.run(timeout=60)
    assert any(c.value.startswith("Reviewed 1 of 28: confirmed 1, raised 0, lowered 0, needs more information 0.") for c in at.caption)
    assert at.get("download_button")[0].proto.disabled is False


# ---- the key and the purpose ----

def test_the_page_says_what_it_is_for_right_now_and_has_a_key(at):
    purpose = " ".join(w.value for w in at.markdown[:3])
    assert "test stage" in purpose and "improve" in purpose and "officers" in purpose
    assert text.KEY_HEADING in [e.label for e in at.expander]
    key = " ".join(m.value for m in at.markdown)
    for term in (text.COL_PRIORITY, text.COL_WHY, text.COL_DETAILS, text.COL_REVIEWER):
        assert f"**{term}**" in key
    assert "Why it is here" not in str(vars(text))
