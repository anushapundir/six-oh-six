from pathlib import Path

from sixohsix.cases import load_cases
from sixohsix.retrieval import search

CASE, _ = load_cases(Path(__file__).parent / "fixtures")[0]


def test_ranks_the_clause_that_answers_the_query_first():
    assert search(CASE.clauses, "royalty on net sales", k=3)[0].id == "c-006"
    assert search(CASE.clauses, "who hosts the software", k=3)[0].id == "c-003"


def test_no_overlap_returns_nothing():
    assert search(CASE.clauses, "xyzzy") == []
