"""P0: the app never touches the answer labels, secrets are ignored, and the banners are in place."""
import re
from pathlib import Path

import config
from triage import text

ROOT = config.ROOT
SKIP = {".venv", ".git", "__pycache__", ".pytest_cache", "tests"}


def python_files():
    return [p for p in ROOT.rglob("*.py") if not any(part in SKIP for part in p.parts)]


def test_the_app_never_reads_the_labels():
    for rel in ("app.py", "views.py", "triage/loader.py", "triage/reference.py", "triage/text.py"):
        src = (ROOT / rel).read_text(encoding="utf-8")
        assert not re.search(r"\blabels\b|load_labels", src), rel


def test_only_the_accuracy_script_may_import_the_labels():
    allowed = {"labels.py", "evaluate.py"}
    for p in python_files():
        if p.name in allowed:
            continue
        src = p.read_text(encoding="utf-8")
        assert not re.search(r"triage\.labels|from triage import .*labels|import labels", src), p.name


def test_the_labels_file_is_not_named_anywhere_but_where_it_belongs():
    for p in python_files():
        if p.name in {"labels.py", "evaluate.py"}:
            continue
        assert "labels.csv" not in p.read_text(encoding="utf-8"), p.name


def test_secrets_are_ignored():
    lines = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for needed in (".env", ".venv/", "*.pdf", ".streamlit/secrets.toml"):
        assert needed in lines


def test_banners_say_synthetic_and_illustrative():
    assert "SYNTHETIC" in text.SYNTHETIC_BANNER
    assert "ILLUSTRATIVE" in text.ILLUSTRATIVE_NOTE and "not company policy" in text.ILLUSTRATIVE_NOTE


def test_the_nothing_sent_sentence_is_allow_listed():
    assert text.NOTHING_SENT in text.ALLOWED_SENTENCES
