from pathlib import Path

import pytest

from sixohsix.cases import load_cases
from sixohsix.schema import Analysis, Consideration, Kind, Obligation, RefObligation, Timing
from sixohsix.score import score

CASE, REF = load_cases(Path(__file__).parent / "fixtures" / "cases")[0]


def perfect() -> Analysis:
    return Analysis(
        reporting_entity=CASE.reporting_entity,
        summary="",
        obligations=[
            Obligation(kind=o.kind, description="", timing=o.timing, rationale="", clauses=o.clauses)
            for o in REF.obligations
        ],
        consideration=Consideration(
            summary="", variable=REF.variable, royalty_exception=REF.royalty_exception, rationale="", clauses=REF.clauses
        ),
    )


def test_perfect_answer_scores_one():
    s = score(perfect(), REF, CASE)
    assert (s.obligation_f1, s.timing_accuracy, s.consideration_correct, s.grounding, s.overall) == (1, 1, 1, 1, 1)
    assert s.hallucinated == []


def test_hallucinated_id_lowers_grounding_and_is_listed():
    a = perfect()
    a.obligations[0].clauses.append("c-999")
    a.consideration.clauses.append("c-999")
    s = score(a, REF, CASE)
    cited = sum(len(o.clauses) for o in a.obligations) + len(a.consideration.clauses)
    assert s.grounding == pytest.approx(1 - 2 / cited)
    assert s.hallucinated == ["c-999"]
    assert s.overall == pytest.approx(s.grounding)


def test_swapped_timing_lowers_timing_only():
    a = perfect()
    for o in a.obligations:
        o.timing = Timing.OVER_TIME if o.timing == Timing.POINT_IN_TIME else Timing.POINT_IN_TIME
    s = score(a, REF, CASE)
    assert s.timing_accuracy == 0
    assert s.obligation_f1 == 1
    assert s.overall == pytest.approx(2 / 3)


def test_duplicate_kinds_count_as_multiset():
    a = perfect()
    a.obligations.append(a.obligations[1].model_copy())  # a second SUPPORT the reference doesn't have
    s = score(a, REF, CASE)
    assert s.obligation_f1 == pytest.approx(2 * (2 / 3) * 1 / (2 / 3 + 1))
    assert s.timing_accuracy == 1

    ref = REF.model_copy(deep=True)
    ref.obligations.append(RefObligation(kind=Kind.SUPPORT, timing=Timing.POINT_IN_TIME, clauses=[], rationale=""))
    s = score(a, ref, CASE)
    assert s.obligation_f1 == 1
    assert s.timing_accuracy == pytest.approx(2 / 3)


def test_wrong_consideration_flags_score_half():
    a = perfect()
    a.consideration.royalty_exception = not REF.royalty_exception
    assert score(a, REF, CASE).consideration_correct == 0.5


def test_citing_nothing_is_ungrounded():
    a = perfect()
    for o in a.obligations:
        o.clauses = []
    a.consideration.clauses = []
    s = score(a, REF, CASE)
    assert s.grounding == 0 and s.overall == 0
