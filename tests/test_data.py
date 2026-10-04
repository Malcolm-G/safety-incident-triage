"""P0: the data files are well formed, and the answer labels are complete and consistent."""
import re
from collections import Counter

from triage.labels import load_labels
from triage.loader import load_info, load_reports
from triage.reference import (LEVELS, load_checklists, load_hazard_flags, load_incident_types,
                              load_instruction_phrases, load_required_details, load_severity_scale)


def test_twenty_eight_reports_parse():
    reports = load_reports()
    assert len(reports) == 28
    ids = [r.report_id for r in reports]
    assert len(set(ids)) == 28 and all(re.fullmatch(r"SYN-\d{3}", i) for i in ids)
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", r.submitted_on) for r in reports)
    assert all(r.text for r in reports)


def test_every_report_is_marked_synthetic():
    assert load_info().label.startswith("SYNTHETIC DATA")
    assert all(r.report_id.startswith("SYN-") for r in load_reports())


def test_the_awkward_cases_are_all_there():
    by_id = {r.report_id: r.text.lower() for r in load_reports()}
    assert any(len(t.split()) <= 5 for t in by_id.values())                         # very short
    assert any("ignore your rules" in t for t in by_id.values())                    # prompt-injection attempt
    assert any("minor" in t and "pain" in t for t in by_id.values())                # clear injury called minor
    assert any("tug drv" in t for t in by_id.values())                              # messy shorthand
    assert any("never touched" in t and "hit the wing tip" in t for t in by_id.values())  # contradicts itself


def test_labels_cover_every_report_with_a_20_8_split():
    labels = load_labels()
    reports = load_reports()
    assert sorted(l.report_id for l in labels) == sorted(r.report_id for r in reports)
    assert Counter(l.split for l in labels) == {"tuning": 20, "holdout": 8}


def test_labels_are_valid():
    type_ids = {t.id for t in load_incident_types()}
    for l in load_labels():
        assert l.expected_type in type_ids and (l.alt_type is None or l.alt_type in type_ids)
        assert l.severity_min in LEVELS and l.severity_max in LEVELS and l.severity_min <= l.severity_max
        assert l.notes


def test_every_incident_type_is_covered_by_the_reports():
    covered = {l.expected_type for l in load_labels()}
    assert covered == {t.id for t in load_incident_types()}
    assert len(load_incident_types()) == 9


def test_both_splits_have_a_spread_of_types():
    for split in ("tuning", "holdout"):
        types = {l.expected_type for l in load_labels() if l.split == split}
        assert len(types) >= 5


def test_every_type_has_a_checklist():
    checklists = load_checklists()
    for t in load_incident_types():
        assert len(checklists.get(t.id, [])) >= 3, t.id
    assert set(checklists) <= {t.id for t in load_incident_types()}


def test_severity_scale_and_flag_minimums_are_one_to_four_only():
    assert [s.level for s in load_severity_scale()] == [1, 2, 3, 4]
    flags = load_hazard_flags()
    assert len(flags) == 11 and all(f.floor in LEVELS for f in flags)
    assert all(f.definition for f in flags)


def test_other_reference_tables():
    assert len(load_required_details()) == 7
    phrases = load_instruction_phrases()
    assert "ignore your rules" in phrases and all(p == p.lower() for p in phrases)
