"""P1 wording tests. PROVISIONAL: the design below is shown to the project owner before anyone relies on it.

What it checks:
  * ONLY app-authored text: triage/text.py (every sentence the page says) and README.md.
    Never report content, labels or example answers, because a report may truthfully say "notified the supervisor".
  * Positive claims that the app notifies, sends, escalates, closes or reports to anyone are refused,
    and so are the words "reportable" and "notifiable".
  * The one required disclaimer, "Nothing is sent or closed.", passes only because it is on a short list
    of EXACT sentences. Another test proves every sentence on that list really appears, so the list cannot rot.
  * Another test keeps model names and technical words out of the page text (README "How it works" is exempt).
  * A structure test makes sure app.py and views.py contain no sentences of their own, so text.py really is
    the only place the page's wording lives.
"""
import ast
import re

import config
from triage import text

ROOT = config.ROOT

BANNED_CLAIMS = [
    (r"\bwe (will |can |may |also )?(notify|send|email|close|report|escalate|alert|inform|tell)\b", "claims the app acts"),
    (r"\b(is|are|was|were|will be|gets|get|been|being) (sent|notified|closed|escalated|emailed|reported|forwarded)\b",
     "claims something is sent, notified, closed or escalated"),
    (r"\b(sent|reported|forwarded|escalated) to\b", "says something goes to someone"),
    (r"\bnotif(y|ies|ied|ication|ications)\b", "mentions notifying"),
    (r"\bauthorit(y|ies)\b", "mentions authorities"),
    (r"\breportable\b|\bnotifiable\b", "decides what is reportable or notifiable"),
    (r"\bescalat\w*", "mentions escalating"),
    (r"\be-?mail\w*", "mentions email"),
]
TECHNICAL_WORDS = re.compile(
    r"\b(claude|haiku|sonnet|opus|anthropic|openai|gpt|llm|model|schema|json|prompt|api|token|tokens)\b", re.I)


def sentences(blob: str) -> list[str]:
    blob = re.sub(r"```.*?```", " ", blob, flags=re.S)           # skip fenced code in the README
    blob = blob.replace("**", "").replace("`", "")
    out = []
    for line in blob.splitlines():
        line = line.strip().lstrip("#|- ").strip()
        out += [s.strip() for s in re.split(r"(?<=[.!?])\s+", line) if s.strip()]
    return out


def problems(sentence: str, allowed=text.ALLOWED_SENTENCES) -> list[str]:
    if sentence in allowed:
        return []
    return [why for pattern, why in BANNED_CLAIMS if re.search(pattern, sentence, re.I)]


def text_py_strings() -> list[str]:
    out = []
    for name, value in vars(text).items():
        if name.startswith("_"):
            continue
        if isinstance(value, str):
            out.append(value)
        elif isinstance(value, (tuple, list)):
            out += [v for v in value if isinstance(v, str)]
        elif isinstance(value, dict):
            out += [v for v in value.values() if isinstance(v, str)]
    return out


def app_text_sentences() -> list[tuple[str, str]]:
    found = [("text.py", s) for blob in text_py_strings() for s in sentences(blob)]
    found += [("README.md", s) for s in sentences((ROOT / "README.md").read_text(encoding="utf-8"))]
    return found


# ---- the real checks ----

def test_the_page_text_and_readme_make_no_claim_of_sending_notifying_or_closing():
    bad = [(src, s, problems(s)) for src, s in app_text_sentences() if problems(s)]
    assert not bad, bad


def test_only_text_py_and_the_readme_are_scanned_never_report_content():
    sources = {src for src, _ in app_text_sentences()}
    assert sources == {"text.py", "README.md"}


def test_every_allowed_sentence_really_appears_so_the_list_cannot_rot():
    present = {s for _, s in app_text_sentences()}
    for allowed in text.ALLOWED_SENTENCES:
        assert allowed in present, allowed
    assert len(text.ALLOWED_SENTENCES) <= 3          # the list must stay short


def test_the_nothing_is_sent_sentence_is_shown_on_the_page():
    assert text.NOTHING_SENT == "Nothing is sent or closed."
    assert text.NOTHING_SENT in text.ALLOWED_SENTENCES


def test_no_model_names_or_technical_words_in_the_page_text():
    bad = [s for blob in text_py_strings() for s in sentences(blob) if TECHNICAL_WORDS.search(s)]
    assert not bad, bad


# ---- the guard itself must work ----

def test_the_guard_catches_positive_claims():
    for bad in ("We notify the supervisor.", "The report is sent to the manager.", "Reported to the authorities.",
                "This is a reportable event.", "A notifiable incident.", "The incident is closed automatically.",
                "We will email the safety team.", "It escalates to the duty manager.", "Everyone is notified."):
        assert problems(bad), bad


def test_the_guard_allows_the_exact_disclaimer_but_not_a_variant():
    assert problems("Nothing is sent or closed.") == []
    assert problems("Nothing is sent or closed automatically.")
    assert problems("Everything is sent or closed.")


def test_the_guard_leaves_ordinary_sentences_alone():
    for ok in ("A person confirms everything.", "Items are flagged for review against your own company's policy.",
               "The rules raised it to High because the report mentions \"ambulance\".",
               "Decisions are kept only while this page is open."):
        assert problems(ok) == [], ok


def test_reports_may_say_notified_and_that_is_fine():
    # a report is data, not app text, so it is never scanned (see the sources test above)
    assert problems("The duty manager was notified straight away.")        # the guard would object ...
    from triage.loader import load_reports
    assert load_reports()                                                    # ... which is why reports are not scanned


# ---- structure: the page's wording lives only in text.py ----

def _sentence_like_literals(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    docstrings = {id(n.body[0].value) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
                  and n.body and isinstance(n.body[0], ast.Expr)
                  and isinstance(n.body[0].value, ast.Constant) and isinstance(n.body[0].value.value, str)}
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docstrings
            and " " in n.value.strip() and len(n.value.strip()) >= 12]


def test_app_and_views_contain_no_sentences_of_their_own():
    for name in ("app.py", "views.py"):
        assert _sentence_like_literals(ROOT / name) == [], name


def test_the_structure_check_would_catch_a_stray_sentence(tmp_path):
    stray = tmp_path / "stray.py"
    stray.write_text('import streamlit as st\nst.write("This sentence should live in the text file.")\n')
    assert _sentence_like_literals(stray)
