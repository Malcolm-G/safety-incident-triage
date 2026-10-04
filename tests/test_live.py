"""Live mode: passcode, caps, and nothing typed is kept, logged or put in an error. No network."""
import os
from types import SimpleNamespace

import pytest
from streamlit.testing.v1 import AppTest

import config
from triage import live, reader
from triage.models import IncidentReading

MARKER = "ZQX-unique-typed-words-7731"


class FakeClient:
    def __init__(self, reply):
        self.reply = reply
        self.messages = SimpleNamespace(parse=self._parse)

    def _parse(self, **kwargs):
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply


def good_reply():
    reading = IncidentReading.model_validate(dict(
        report_id="LIVE", incident_type="equipment_fault", suggested_severity=1, rating_reason="Nobody was hurt.",
        hazard_flags=[], missing_details=[], summary="Something stopped."))
    return SimpleNamespace(parsed_output=reading, stop_reason="end_turn", model="m",
                           usage=SimpleNamespace(input_tokens=1, output_tokens=1))


@pytest.fixture(autouse=True)
def fresh_counters():
    live._day.update(date=live.date.today(), count=0)


def unlocked():
    return live.LiveSession(unlocked=True)


def test_live_mode_does_not_exist_without_a_passcode(monkeypatch):
    monkeypatch.delenv("LIVE_PASSCODE", raising=False)
    assert not live.enabled()


def test_the_passcode_gate(monkeypatch):
    monkeypatch.setenv("LIVE_PASSCODE", "open-sesame")
    s = live.LiveSession()
    assert not live.unlock(s, "wrong") and not s.unlocked and s.bad_tries == 1
    assert live.unlock(s, "open-sesame") and s.unlocked


def test_too_many_wrong_tries_locks_even_the_right_passcode(monkeypatch):
    monkeypatch.setenv("LIVE_PASSCODE", "open-sesame")
    s = live.LiveSession()
    for _ in range(live.MAX_BAD_PASSCODES):
        live.unlock(s, "nope")
    assert s.locked_out and not live.unlock(s, "open-sesame")


def test_a_locked_session_cannot_submit(ref):
    assert live.submit("a report", ref, live.LiveSession(), lambda: FakeClient(good_reply())).status == live.EMPTY


def test_caps(ref):
    mk = lambda: FakeClient(good_reply())
    assert live.submit("   ", ref, unlocked(), mk).status == live.EMPTY
    assert live.submit("x" * (live.MAX_CHARS + 1), ref, unlocked(), mk).status == live.TOO_LONG
    s = unlocked()
    for _ in range(live.MAX_PER_SESSION):
        assert live.submit("a loader dropped a bag", ref, s, mk).status == live.OK
    assert live.submit("another", ref, s, mk).status == live.SESSION_LIMIT
    live._day["count"] = live.MAX_PER_DAY
    assert live.submit("fresh visitor", ref, unlocked(), mk).status == live.DAY_LIMIT


def test_no_key_gives_a_plain_status(ref, monkeypatch):
    def no_key():
        raise reader.MissingKey("x")
    assert live.submit("a report", ref, unlocked(), no_key).status == live.NO_KEY


def test_a_failed_read_still_goes_up(ref):
    got = live.submit("a report", ref, unlocked(), lambda: FakeClient(RuntimeError(MARKER)))
    assert got.status == live.OK and got.triage.needs_person and got.triage.final_severity == 4
    assert MARKER not in repr(got)


def tree():
    skip = {".git", ".venv", "__pycache__", ".pytest_cache"}
    out = {}
    for root, dirs, files in os.walk(config.ROOT):
        dirs[:] = [d for d in dirs if d not in skip]
        for f in files:
            p = os.path.join(root, f)
            st = os.stat(p)
            out[p] = (st.st_size, st.st_mtime_ns)
    return out


@pytest.mark.parametrize("reply", [good_reply(), RuntimeError(MARKER), None])
def test_typed_text_is_not_written_printed_or_logged(ref, reply, capsys, caplog, tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    before = tree()
    live.submit(f"{MARKER} a loader dropped a bag", ref, unlocked(), lambda: FakeClient(reply))
    out = capsys.readouterr()
    assert MARKER not in out.out + out.err + caplog.text
    assert tree() == before and not list(tmp_path.iterdir())


def live_app(monkeypatch):
    monkeypatch.setattr(config, "load_dotenv", lambda: None)
    monkeypatch.setenv("DATASET", "synthetic")
    monkeypatch.setenv("LIVE_PASSCODE", "open-sesame")
    monkeypatch.setattr(config, "ANSWERS", "fixture")
    monkeypatch.setattr(reader, "make_client", lambda: FakeClient(good_reply()))
    return AppTest.from_file(str(config.ROOT / "app.py")).run(timeout=60)


def test_the_page_has_the_tab_the_privacy_line_and_a_locked_box(monkeypatch):
    from triage import text
    app = live_app(monkeypatch)
    assert not app.exception
    assert any(w.value == text.LIVE_PRIVACY for w in app.warning)
    assert len(app.tabs) == 4
    assert not [t for t in app.text_area if t.key == "live_text"]


def test_wrong_then_right_passcode_then_a_read_that_is_not_kept(monkeypatch):
    from triage import text
    app = live_app(monkeypatch)
    app.text_input(key="live_code").set_value("wrong")
    [b for b in app.button if b.label == text.LIVE_UNLOCK][0].click()
    app.run(timeout=60)
    assert any(e.value == text.LIVE_WRONG_PASSCODE for e in app.error)
    app.text_input(key="live_code").set_value("open-sesame")
    [b for b in app.button if b.label == text.LIVE_UNLOCK][0].click()
    app.run(timeout=60)
    app.text_area(key="live_text").set_value(f"{MARKER} a loader dropped a bag")
    [b for b in app.button if b.label == text.LIVE_READ_BUTTON][0].click()
    app.run(timeout=60)
    assert not app.exception and any(w.value == text.LIVE_BANNER for w in app.warning)
    assert app.text_area(key="live_text").value == ""
    assert MARKER not in repr(app.session_state)
    assert not any(MARKER in str(getattr(el, "value", "")) for el in [*app.markdown, *app.text, *app.caption])
