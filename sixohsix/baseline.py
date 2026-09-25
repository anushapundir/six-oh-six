"""The spreadsheet approach: keyword rules over clauses, no judgment. The bar the agent has to clear."""

import re
from typing import Literal, NamedTuple

from sixohsix.schema import KINDS, Analysis, Case, Clause, Consideration, Kind, Obligation


class Rule(NamedTuple):
    target: Kind | Literal["variable", "royalty_exception"]
    pattern: re.Pattern[str]


def rx(p: str) -> re.Pattern[str]:
    return re.compile(p, re.IGNORECASE)


# Order sets output order. Every rule that matches a clause fires; nothing weighs one against another.
RULES: list[Rule] = [
    Rule(Kind.SAAS, rx(r"\b(hosted|hosting|software[- ]as[- ]a[- ]service|saas|cloud|subscription)\b")),
    Rule(Kind.LICENSE_FUNCTIONAL, rx(r"\blicen[cs]e\b")),
    Rule(Kind.LICENSE_SYMBOLIC, rx(r"\b(trademarks?|brand|logos?|franchise)\b")),
    Rule(Kind.SUPPORT, rx(r"\b(support|maintenance|updates?|upgrades?)\b")),
    Rule(Kind.SERVICES, rx(r"\b(implementation|consulting|professional services|training|development)\b")),
    Rule(Kind.GOODS, rx(r"\b(ship(ment|ped)?|hardware|equipment|units|inventory)\b")),
    Rule("variable", rx(r"\b(fees?|royalt(y|ies)|usage|rebates?|bonus|milestones?|penalt(y|ies)|credits?)\b")),
    Rule("royalty_exception", rx(r"\broyalt(y|ies)\b")),
]


def matches(rule: Rule, clauses: list[Clause]) -> list[str]:
    return [c.id for c in clauses if rule.pattern.search(f"{c.heading} {c.text}")]


def analyze(case: Case) -> Analysis:
    hits = {rule.target: matches(rule, case.clauses) for rule in RULES}
    obligations = [
        Obligation(
            kind=kind,
            description=KINDS[kind].label,
            timing=KINDS[kind].usual_timing,
            rationale=f"Keyword rule for '{KINDS[kind].label}' matched {len(ids)} clause(s).",
            clauses=ids,
            guidance=list(KINDS[kind].guidance),
        )
        for kind, ids in hits.items()
        if isinstance(kind, Kind) and ids
    ]
    variable, royalty = hits["variable"], hits["royalty_exception"]
    return Analysis(
        reporting_entity=case.reporting_entity,
        summary=f"Keyword rules found {len(obligations)} obligation type(s) across {len(case.clauses)} clauses.",
        obligations=obligations,
        consideration=Consideration(
            summary="Fee, royalty, usage and incentive keywords." if variable else "No variable-pricing keywords found.",
            variable=bool(variable),
            royalty_exception=bool(royalty),
            rationale="Any fee or pricing keyword is treated as variable; any royalty keyword triggers the exception.",
            clauses=list(dict.fromkeys(variable + royalty)),
        ),
    )
