"""Shared test helpers."""
import pytest

import config
from triage.fixtures import load_fixture_outcomes
from triage.loader import load_reports
from triage.priority import build_queue, triage_report
from triage.reference import load_reference


@pytest.fixture(scope="session")
def ref():
    return load_reference()


@pytest.fixture(scope="session")
def reports():
    return load_reports()


@pytest.fixture(scope="session")
def by_id(reports):
    return {r.report_id: r for r in reports}


@pytest.fixture(scope="session")
def outcomes(reports):
    return load_fixture_outcomes([r.report_id for r in reports])


@pytest.fixture(scope="session")
def queue(reports, outcomes, ref):
    return build_queue(reports, outcomes, ref)


@pytest.fixture
def triage_of(by_id, ref):
    def make(report_id, outcome, text=None):
        report = by_id[report_id]
        if text is not None:
            from dataclasses import replace
            report = replace(report, text=text)
        return triage_report(report, outcome, ref)
    return make
