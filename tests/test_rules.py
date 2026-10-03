"""P1: the rules that set priority, in pure code."""
import itertools

import pytest
from pydantic import ValidationError

from triage import text
from triage.keywords import read_report
from triage.models import Failure, IncidentReading
from triage.priority import final_severity, sort_key, triage_report


def reading(report_id, severity, incident_type="other", missing=(), injury="no", damage="no", summary="A thing happened."):
    return IncidentReading(report_id=report_id, incident_type=incident_type, suggested_severity=severity,
                           missing_details=list(missing), injury_mentioned=injury, damage_mentioned=damage,
                           summary=summary)


# ---- the floor only raises ----

@pytest.mark.parametrize("suggested,floor", list(itertools.product([1, 2, 3, 4], [0, 1, 2, 3, 4])))
def test_final_severity_is_never_below_the_suggestion_or_the_floor(suggested, floor):
    final = final_severity(suggested, floor)
    assert final == max(suggested, floor)
    assert final >= suggested and final >= floor


def test_no_usable_answer_means_the_top_never_low():
    for floor in range(0, 5):
        assert final_severity(None, floor) == 4


def test_a_low_suggestion_is_raised_by_a_high_floor(triage_of):
    t = triage_of("SYN-002", reading("SYN-002", 1, "manual_handling", injury="yes"))
    assert t.suggested_severity == 1 and t.floor == 3 and t.final_severity == 3
    assert t.disagree
    assert any("raised it to High" in r and "hurt" in r or "pain" in r for r in t.reasons)


def test_the_floor_never_lowers_a_high_suggestion(triage_of):
    t = triage_of("SYN-006", reading("SYN-006", 4, "foreign_object_debris"))
    assert t.floor == 0 and t.final_severity == 4


def test_when_the_reader_and_rules_agree_the_reason_says_so(triage_of):
    t = triage_of("SYN-016", reading("SYN-016", 4, "slip_trip_fall", injury="yes"))
    assert not t.disagree and t.reasons[0].startswith("The AI reader's suggestion stands")


# ---- failures go UP ----

@pytest.mark.parametrize("kind", list(Failure))
def test_every_kind_of_failure_goes_to_the_top_with_its_reason(triage_of, kind):
    # SYN-006 is a harmless loose-bolt report: if anything could drift to "low", it would be this one
    t = triage_of("SYN-006", kind)
    assert t.failed and t.final_severity == 4 and t.reading is None and t.suggested_severity is None
    assert t.reasons[0] == text.FAILURE_REASONS[kind.value]


def test_every_failure_kind_has_a_plain_reason():
    assert set(text.FAILURE_REASONS) == {k.value for k in Failure}


def test_a_report_with_no_outcome_at_all_is_a_failure(reports, ref):
    from triage.priority import build_queue
    queue = build_queue(reports, {}, ref)
    assert len(queue) == 20 and all(t.failed and t.final_severity == 4 for t in queue)


# ---- queue order ----

def test_queue_is_most_urgent_first_with_failures_first_inside_a_band(queue):
    assert [t.final_severity for t in queue] == sorted((t.final_severity for t in queue), reverse=True)
    top = [t for t in queue if t.final_severity == 4]
    failures = [t for t in top if t.failed]
    assert top[:len(failures)] == failures and failures                      # failures lead the top band
    assert queue[0].report_id == "SYN-006"


def test_order_inside_a_band_goes_disagree_then_most_missing_then_id(queue):
    for band in (4, 3, 2, 1):
        items = [t for t in queue if t.final_severity == band and not t.failed]
        assert items == sorted(items, key=lambda t: (not t.disagree, -t.missing_count, t.report_id))


def test_sort_key_orders_by_severity_first():
    from dataclasses import replace
    a = replace_triage_severity(3)
    b = replace_triage_severity(4)
    assert sorted([a, b], key=sort_key)[0] is b


def replace_triage_severity(n):
    from triage.models import Triage
    return Triage("X", None, None, n, 0, n, False, False, (), False, False, (), ())


# ---- disagreement conflicts ----

def test_serious_injury_words_with_an_AI_answer_of_no_injury_are_flagged(triage_of):
    t = triage_of("SYN-016", reading("SYN-016", 4, "slip_trip_fall", injury="no"))
    assert t.disagree and text.REASON_INJURY_CONFLICT in t.reasons


def test_plain_injury_words_alone_do_not_flag_a_conflict(triage_of):
    # "nobody was hurt" contains an injury word; that must not count as a disagreement by itself
    t = triage_of("SYN-019", reading("SYN-019", 3, "near_miss", injury="no"))
    assert t.floor == 3 and not t.disagree and text.REASON_INJURY_CONFLICT not in t.reasons


def test_damage_words_with_an_AI_answer_of_no_damage_are_flagged(triage_of):
    t = triage_of("SYN-001", reading("SYN-001", 3, "aircraft_contact", damage="no"))
    assert t.disagree and text.REASON_DAMAGE_CONFLICT in t.reasons


# ---- required details ----

def test_missing_details_are_counted_and_listed_in_plain_words(triage_of):
    t = triage_of("SYN-010", reading("SYN-010", 1, "near_miss", missing=["who", "where", "when"]))
    assert t.missing_count == 3 and t.incomplete
    assert any("Who was involved" in r and "Where it happened" in r for r in t.reasons)


def test_a_complete_report_is_not_incomplete(triage_of):
    t = triage_of("SYN-001", reading("SYN-001", 3, "aircraft_contact", damage="yes"))
    assert not t.incomplete and t.missing_count == 0


def test_a_very_short_report_is_always_incomplete(triage_of):
    t = triage_of("SYN-013", reading("SYN-013", 1, missing=[]))
    assert t.very_short and t.incomplete and text.REASON_SHORT in t.reasons


# ---- checklist ----

def test_the_checklist_comes_from_the_type_and_failures_get_the_general_one(triage_of, ref):
    t = triage_of("SYN-004", reading("SYN-004", 3, "fuel_spill"))
    assert list(t.checklist) == ref.checklists["fuel_spill"]
    assert list(triage_of("SYN-006", Failure.timed_out).checklist) == ref.checklists["other"]


# ---- prompt injection ----

def test_every_instruction_phrase_in_the_table_is_caught(ref):
    for phrase in ref.instruction_phrases:
        code = read_report(f"A cart was moved. {phrase.upper()} now.", ref.keywords, ref.instruction_phrases)
        assert code.instruction_like, phrase


def test_the_injection_report_is_flagged_and_changes_nothing_else(by_id, ref, triage_of):
    from dataclasses import replace
    injected = by_id["SYN-014"]
    assert "ignore your rules" in injected.text.lower()
    clean_text = injected.text.split("NOTE TO THE REVIEWING SYSTEM")[0] + "The cart was secured afterwards and nobody was hurt."
    obeyed = reading("SYN-014", 1, "other")                 # the AI reader did what the planted text asked
    t_injected = triage_of("SYN-014", obeyed)
    t_clean = triage_of("SYN-014", obeyed, text=clean_text)

    assert t_injected.instruction_like and not t_clean.instruction_like
    assert text.REASON_INSTRUCTION in t_injected.reasons
    # the planted text has no effect on anything the code decides
    assert (t_injected.floor, t_injected.final_severity, t_injected.disagree, t_injected.missing) == \
           (t_clean.floor, t_clean.final_severity, t_clean.disagree, t_clean.missing)
    # and the rules still lift the report back up, whatever the AI reader was talked into
    assert t_injected.final_severity == 3


def test_instruction_text_can_never_lower_a_priority(by_id, ref, triage_of):
    base_text = by_id["SYN-016"].text
    for phrase in ref.instruction_phrases:
        t = triage_of("SYN-016", reading("SYN-016", 4, "slip_trip_fall", injury="yes"), text=base_text + " " + phrase)
        assert t.final_severity == 4


# ---- the AI reader's fixed fields ----

def test_the_reader_has_exactly_the_seven_fixed_fields_and_nothing_that_acts():
    fields = set(IncidentReading.model_fields)
    assert fields == {"report_id", "incident_type", "suggested_severity", "missing_details",
                      "injury_mentioned", "damage_mentioned", "summary"}
    for banned in ("instruction", "advice", "action", "priority", "queue", "notify", "send", "close", "decision"):
        assert not [f for f in fields if banned in f], banned


@pytest.mark.parametrize("change", [
    {"extra_field": "ignore the rules"},
    {"suggested_severity": 5}, {"suggested_severity": 0}, {"suggested_severity": "high"},
    {"incident_type": "made_up_type"}, {"injury_mentioned": "maybe"},
    {"missing_details": ["who", "who"]}, {"missing_details": ["shoe_size"]},
    {"summary": ""}, {"summary": "   "}, {"summary": "x" * 301},
])
def test_bad_fields_are_refused(change):
    good = dict(report_id="SYN-001", incident_type="other", suggested_severity=2, missing_details=[],
                injury_mentioned="no", damage_mentioned="no", summary="A thing happened.")
    IncidentReading.model_validate(good)
    with pytest.raises(ValidationError):
        IncidentReading.model_validate({**good, **change})


def test_the_allowed_values_match_the_visible_tables(ref):
    import typing
    from triage.models import DetailId, IncidentTypeId
    assert set(typing.get_args(IncidentTypeId)) == set(ref.type_names)
    assert set(typing.get_args(DetailId)) == set(ref.details)


def test_only_the_extractor_may_import_the_ai_library():
    import re
    import config
    for p in config.ROOT.rglob("*.py"):
        if any(part in {".venv", ".git", "__pycache__", "tests"} for part in p.parts) or p.name == "extractor.py":
            continue
        assert not re.search(r"^\s*(import|from)\s+anthropic", p.read_text(encoding="utf-8"), re.M), p.name
