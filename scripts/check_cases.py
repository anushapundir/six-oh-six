"""Validate every data/cases/<id>/ against sixohsix.schema and check each citation resolves.

    python scripts/check_cases.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sixohsix.schema import Case, Reference  # noqa: E402

MAX_CHARS = 2500


def check(case_dir: Path) -> list[str]:
    case = Case.model_validate_json((case_dir / "case.json").read_text())
    ref = Reference.model_validate_json((case_dir / "reference.json").read_text())
    ids = [c.id for c in case.clauses]
    headings = {c.id: c.heading for c in case.clauses}
    errors = []
    if case.id != case_dir.name:
        errors.append(f"id {case.id!r} does not match folder")
    if ids != [f"c-{i:03d}" for i in range(1, len(ids) + 1)]:
        errors.append("clause ids are not c-001.. in order")
    errors += [f"{c.id} is {len(c.text)} chars" for c in case.clauses if len(c.text) > MAX_CHARS]
    errors += [f"{f} is empty" for f in ("title", "reporting_entity", "customer", "why_hard", "source") if not getattr(case, f)]
    cited = [("consideration", ref.clauses)] + [(f"{o.kind.value}", o.clauses) for o in ref.obligations]
    for label, clause_ids in cited:
        if not clause_ids:
            errors.append(f"{label} cites no clauses")
        errors += [f"{label} cites missing {cid}" for cid in clause_ids if cid not in headings]
    for o in ref.obligations:
        if not o.rationale.strip():
            errors.append(f"{o.kind.value} has no rationale")
    print(f"{case.id}: {len(ids)} clauses, {len(ref.obligations)} obligations, status={ref.status}")
    for label, clause_ids in cited:
        print(f"  {label:<20} " + "; ".join(f"{cid} {headings.get(cid, '???')[:32]}" for cid in clause_ids))
    return errors


if __name__ == "__main__":
    failures = {d.name: errs for d in sorted((ROOT / "data" / "cases").iterdir()) if d.is_dir() and (errs := check(d))}
    for name, errs in failures.items():
        print(f"FAIL {name}: " + "; ".join(errs))
    sys.exit(1 if failures else 0)
