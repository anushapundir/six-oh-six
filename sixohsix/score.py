"""Grade an Analysis against hand labels. Pure: no I/O."""

from collections import Counter
from statistics import mean

from sixohsix.schema import Analysis, Case, Reference, Scores


def obligation_f1(analysis: Analysis, ref: Reference) -> float:
    pred = Counter(o.kind for o in analysis.obligations)
    gold = Counter(o.kind for o in ref.obligations)
    if not pred and not gold:
        return 1.0
    hit = (pred & gold).total()
    if hit == 0:
        return 0.0
    p, r = hit / pred.total(), hit / gold.total()
    return 2 * p * r / (p + r)


def timing_accuracy(analysis: Analysis, ref: Reference) -> float:
    pred_k = Counter(o.kind for o in analysis.obligations)
    gold_k = Counter(o.kind for o in ref.obligations)
    matched = (pred_k & gold_k).total()
    if matched == 0:
        return 1.0 if not ref.obligations else 0.0
    # Pairing within a kind is order-free: count (kind, timing) overlaps.
    pred_kt = Counter((o.kind, o.timing) for o in analysis.obligations)
    gold_kt = Counter((o.kind, o.timing) for o in ref.obligations)
    return (pred_kt & gold_kt).total() / matched


def consideration_correct(analysis: Analysis, ref: Reference) -> float:
    c = analysis.consideration
    return mean([c.variable == ref.variable, c.royalty_exception == ref.royalty_exception])


def cited_ids(analysis: Analysis) -> list[str]:
    return [i for o in analysis.obligations for i in o.clauses] + analysis.consideration.clauses


def grounding(analysis: Analysis, case: Case) -> tuple[float, list[str]]:
    """Share of cited ids that exist, and the ones that don't. Citing nothing grounds nothing."""
    known = {c.id for c in case.clauses}
    cited = cited_ids(analysis)
    if not cited:
        return 0.0, []
    missing = [i for i in cited if i not in known]
    return 1 - len(missing) / len(cited), list(dict.fromkeys(missing))


def score(analysis: Analysis, ref: Reference, case: Case) -> Scores:
    f1 = obligation_f1(analysis, ref)
    timing = timing_accuracy(analysis, ref)
    cons = consideration_correct(analysis, ref)
    ground, hallucinated = grounding(analysis, case)
    return Scores(
        obligation_f1=f1,
        timing_accuracy=timing,
        consideration_correct=cons,
        grounding=ground,
        hallucinated=hallucinated,
        overall=mean([f1, timing, cons]) * ground,
    )
