"""P1: the page shows the queue, the report card, the reviewer panel and the checks, and behaves."""
import pytest
from streamlit.testing.v1 import AppTest

import config
from triage import text


def fresh_app(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("DATASET", "synthetic")
    return AppTest.from_file(str(config.ROOT / "app.py"))


@pytest.fixture
def at(monkeypatch):
    return fresh_app(monkeypatch).run(timeout=60)


def plain(value) -> str:
    return str(value).replace("\\", "")        # table cells are Markdown-escaped; compare what a person sees


def queue_rows(app):
    return app.table[0].value


def test_page_shows_banners_checks_and_the_nothing_sent_line(at):
    assert not at.exception
    assert [t.value for t in at.title] == [text.APP_TITLE]
    assert any(w.value.startswith("SYNTHETIC DATA") for w in at.warning)
    assert any(w.value.startswith("HAND-WRITTEN EXAMPLE ANSWERS") for w in at.warning)
    assert any(i.value.startswith("ILLUSTRATIVE ASSUMPTIONS") for i in at.info)
    assert any(text.NOTHING_SENT in c.value for c in at.caption)
    assert any(s.value == text.CHECKS_ALL_PASSED.format(n=4) for s in at.success)


def test_the_queue_has_twenty_reports_failure_first(at):
    rows = queue_rows(at)
    assert len(rows) == 20
    assert plain(rows.iloc[0][text.COL_REPORT]) == "SYN-006"
    assert plain(rows.iloc[0][text.COL_PRIORITY]) == text.BAND_NEEDS_PERSON
    assert plain(rows.iloc[0][text.COL_AI]) == text.AI_NO_ANSWER


def test_why_it_is_here_gives_plain_reasons_not_a_story_about_who_decided(at):
    rows = queue_rows(at)
    why = {plain(r[text.COL_REPORT]): plain(r[text.COL_WHY]) for _, r in rows.iterrows()}
    assert why["SYN-002"] == "Someone was hurt"
    assert why["SYN-016"] == "Serious injury | Someone was hurt"
    assert why["SYN-004"] == "Fuel leaked or spilled"
    assert why["SYN-006"] == text.FAILURE_REASONS["timed_out"]
    assert why["SYN-014"] == text.REASON_INSTRUCTION
    for report_id, line in why.items():
        for narration in ("AI reader suggested", "Its own answers", "raised it", "disagree", "the rules"):
            assert narration not in line, (report_id, line)


def test_the_card_shows_three_separate_things(at):
    shown = " ".join(m.value for m in at.markdown)
    for heading in (text.CARD_AI_HEADING, text.CARD_RULES_HEADING, text.CARD_REVIEWER_HEADING,
                    text.REVIEWER_HEADING, text.MISSING_HEADING, text.CHECKLIST_HEADING):
        assert heading in shown
    assert not at.exception


def test_the_chart_and_the_all_reports_table_are_there(at):
    assert len(at.get("vega_lite_chart")) >= 1
    assert len(at.table[1].value) == 20


def test_tabs_are_tracked_so_a_rerun_keeps_the_open_tab(at):
    assert "main_tabs" in at.session_state


def test_opening_another_report_shows_its_card(at):
    at.selectbox(key="open_report").set_value("SYN-016").run(timeout=60)
    assert not at.exception
    assert any("badly hurt his wrist" in t.value for t in at.text)


# ---- reviewer flow ----

def fill(app, name, action, severity=None, reason="", report="SYN-006"):
    app.text_input(key="reviewer_name").set_value(name)
    app.radio(key=f"action_{report}").set_value(action).run(timeout=60)   # the severity box unlocks after this
    if severity is not None:
        app.selectbox(key=f"severity_{report}").set_value(severity)
    app.text_area(key=f"reason_{report}").set_value(reason)


def test_lowering_without_a_reason_is_refused_and_nothing_is_saved(at):
    before = queue_rows(at).copy()
    fill(at, "Sam Lee", text.ACTION_CHANGE, severity=2, reason="")
    at.button(key="save_SYN-006").click()
    at.run(timeout=60)
    assert any(text.ERR_REASON in e.value for e in at.error)
    assert len(at.session_state["decisions"]) == 0
    assert plain(queue_rows(at).iloc[0][text.COL_REVIEWER]) == text.STATUS_WAITING
    assert queue_rows(at).equals(before)


def test_a_lowered_item_stays_visible_as_overruled_and_the_queue_does_not_move(at):
    order_before = [plain(x) for x in queue_rows(at)[text.COL_REPORT]]
    priority_before = [plain(x) for x in queue_rows(at)[text.COL_PRIORITY]]
    fill(at, "Sam Lee", text.ACTION_CHANGE, severity=2, reason="Checked with the lead, it was a harmless item.")
    at.button(key="save_SYN-006").click()
    at.run(timeout=60)
    assert not at.exception and not at.error
    assert any(text.SAVED_OK in s.value for s in at.success)
    rows = queue_rows(at)
    assert "Overruled by Sam Lee: Checked with the lead" in plain(rows.iloc[0][text.COL_REVIEWER])
    # the computed result and the queue order are exactly what they were
    assert [plain(x) for x in rows[text.COL_REPORT]] == order_before
    assert [plain(x) for x in rows[text.COL_PRIORITY]] == priority_before
    # the card shows the overrule next to, not instead of, the computed priority
    shown = " ".join(w.value for w in at.markdown) + " " + " ".join(t.value for t in at.text) + " " + \
            " ".join(w.value for w in at.get("markdown"))
    assert any("Overruled by Sam Lee" in plain(t.value) for t in at.text) or "Overruled by Sam Lee" in plain(shown)


def test_confirming_needs_a_name(at):
    fill(at, "", text.ACTION_CONFIRM)
    at.button(key="save_SYN-006").click()
    at.run(timeout=60)
    assert any(text.ERR_NAME in e.value for e in at.error)


def test_confirming_is_saved_without_a_reason(at):
    fill(at, "Sam Lee", text.ACTION_CONFIRM)
    at.button(key="save_SYN-006").click()
    at.run(timeout=60)
    assert not at.error
    assert "Confirmed by Sam Lee" in plain(queue_rows(at).iloc[0][text.COL_REVIEWER])


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
