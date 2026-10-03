"""P0: the skeleton page shows the banner, the scale box and all 20 reports."""
from streamlit.testing.v1 import AppTest

import config
from triage import text


def run_app(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("DATASET", "synthetic")
    return AppTest.from_file(str(config.ROOT / "app.py")).run(timeout=60)


def test_page_shows_banners_scale_and_twenty_reports(monkeypatch):
    at = run_app(monkeypatch)
    assert not at.exception
    assert [t.value for t in at.title] == [text.APP_TITLE]
    warnings = [w.value for w in at.warning]
    assert any(w.startswith("SYNTHETIC DATA") for w in warnings)
    # the illustrative notice is on the page itself, not hidden inside the collapsed scale box
    assert any(i.value.startswith("ILLUSTRATIVE ASSUMPTIONS") for i in at.info)
    reports_table = at.table[-1].value
    assert len(reports_table) == 20


def test_report_text_is_shown_literally_never_as_a_link(monkeypatch):
    from views import md_escape
    hostile = "![x](http://a.example/p.png) **bold** <b>hi</b> [a](http://b.example)"
    out = md_escape(hostile)
    assert "http://" not in out and "<b>" not in out and "\\*\\*bold\\*\\*" in out


def test_missing_dataset_gives_a_plain_message(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("DATASET", "does_not_exist")
    monkeypatch.setattr(config, "DATASET", "does_not_exist")
    at = AppTest.from_file(str(config.ROOT / "app.py")).run(timeout=60)
    assert not at.exception
    assert any(text.DATA_MISSING in e.value for e in at.error)
