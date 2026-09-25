"""Okapi BM25 over clause heading and text."""

import math
import re
from collections import Counter

from sixohsix.schema import Clause

K1, B = 1.5, 0.75


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def search(clauses: list[Clause], query: str, k: int = 5) -> list[Clause]:
    # Re-indexes per call: contracts are tens of clauses. Cache the index if that changes.
    docs = [Counter(tokens(f"{c.heading} {c.text}")) for c in clauses]
    if not docs:
        return []
    avg = sum(d.total() for d in docs) / len(docs)
    df = Counter(t for d in docs for t in d)
    n = len(docs)

    def bm25(d: Counter) -> float:
        s = 0.0
        for t in set(tokens(query)):
            if t in d:
                idf = math.log(1 + (n - df[t] + 0.5) / (df[t] + 0.5))
                s += idf * d[t] * (K1 + 1) / (d[t] + K1 * (1 - B + B * d.total() / avg))
        return s

    ranked = sorted(((bm25(d), i) for i, d in enumerate(docs)), key=lambda x: -x[0])
    return [clauses[i] for s, i in ranked[:k] if s > 0]
