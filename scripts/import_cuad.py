"""Turn CUAD full-contract .txt files into data/cases/<id>/case.json clauses.

    python scripts/import_cuad.py /path/to/CUAD_v1/full_contract_txt

Clause text is verbatim; only page-break noise and blank form lines are removed. Case
metadata already in case.json (title, reporting_entity, why_hard, ...) is kept, so reruns
only refresh clauses.
"""

import json
import re
import sys
from pathlib import Path
from typing import NamedTuple

MAX_CHARS = 2500
CASES_DIR = Path(__file__).resolve().parent.parent / "data" / "cases"


class Source(NamedTuple):
    files: tuple[str, ...]  # CUAD file names, in reading order
    strip: tuple[str, ...] = ()  # page-header patterns this filing repeats
    subitem: str | None = None  # numbered lines that are list items, not sections


CASES: dict[str, Source] = {
    "egain-hosting": Source(
        ("WEBHELPCOMINC_03_22_2000-EX-10.8-HOSTING AGREEMENT.txt",),
        strip=(r"^eGAIN COMMUNICATIONS CORPORATION$", r"^HOSTING AGREEMENT$"),
    ),
    "garman-license-maintenance": Source(
        ("SPARKLINGSPRINGWATERHOLDINGSLTD_07_03_2002-EX-10.13-SOFTWARE LICENSE AND MAINTENANCE AGREEMENT.txt",),
    ),
    "jhu-patent-royalty": Source(
        ("VirtuosoSurgicalInc_20191227_1-A_EX1A-6 MAT CTRCT_11933379_EX1A-6 MAT CTRCT_License Agreement.txt",),
        strip=(r"^May 3, 2016 (?=\S)",),
    ),
    "ssd-app-development": Source(
        (
            "PelicanDeliversInc_20200211_S-1_EX-10.3_11975895_EX-10.3_Development Agreement2.txt",
            "PelicanDeliversInc_20200211_S-1_EX-10.3_11975895_EX-10.3_Development Agreement1.txt",
        ),
    ),
    "airsopure-franchise": Source(
        ("AIRTECHINTERNATIONALGROUPINC_05_08_2000-EX-10.4-FRANCHISE AGREEMENT.txt",),
        subitem=r"^\d{1,2}\.\s+(?![A-Z]{2,}\b)",
    ),
    "fcc-terpene-supply": Source(
        ("FLOTEKINDUSTRIESINCCN_05_09_2019-EX-10.1-SUPPLY AGREEMENT.txt",),
    ),
}

NOISE = [
    re.compile(p, re.I)
    for p in (
        r"^source: .*$",  # EDGAR page footer
        r"^\d{1,3}$",  # bare page number
        r"^page \d+$",
        r"^exhibit [\d.]+$",  # SEC exhibit label
        r"^\[(logo|form)\]$",
    )
]
BLANKS = re.compile(r"^- (?=[-_]{5})|[-_]{5,}")

# "3. GRANT", "4.2 Minimum Annual Royalties:", "3.01. In consideration", "Section 1. SERVICES."
SECTION = re.compile(r"^(?:Section\s+)?(\d{1,2})(?:\.\d{1,2})*\.?\s+\S")
ANNEX = re.compile(r"^(EXHIBIT|SCHEDULE|APPENDIX|STATEMENT OF WORK)\b")
SIGNATURE = re.compile(r"^(IN WITNESS WHEREOF|Dated the\b|EXECUTED on this\b|Each party agrees to the terms)", re.I)
# Numbered starts buried mid-paragraph: after sentence punctuation for "N.N", or any "N. CAPS" run.
INLINE_SUB = re.compile(r"(?<=[.:;)])\s+(?=\d{1,2}\.\d{1,2}\.?\s+[A-Z\"])")
INLINE_TOP = re.compile(r"\s+(?=\d{1,2}\.\s+[A-Z]{3,}\b)")
SMALL_WORDS = {"of", "and", "or", "the", "to", "for", "in", "on", "a", "an", "by", "with", "&"}


def paragraphs(text: str, strip: tuple[str, ...]) -> list[str]:
    extra = [re.compile(p) for p in strip]
    paras: list[str] = []
    for raw in text.splitlines():
        line = BLANKS.sub("", re.sub(r"[ \t ]+", " ", raw)).strip()
        for pat in extra:
            line = pat.sub("", line).strip()
        line = re.sub(r" {2,}", " ", line)
        if not line or any(n.match(line) for n in NOISE):
            continue
        # A line that starts lowercase continues the paragraph a page break cut.
        if paras and line[0].islower():
            paras[-1] += " " + line
            continue
        for piece in INLINE_TOP.split(line):
            paras.extend(p for p in INLINE_SUB.split(piece) if p)
    return paras


def is_caps_heading(p: str) -> bool:
    letters = [c for c in p if c.isalpha()]
    return (
        len(p) <= 70
        and len(letters) >= 4
        and p.upper() == p
        and not p.startswith("(")
        and not re.match(r"^[A-Z]\.\s", p)
    )


SENTENCE_OPENERS = {"This", "The", "You", "Your", "If", "In", "Any", "Should", "Provided", "Except", "At", "During", "Each", "All", "It", "Unless", "Notwithstanding"}


def title_run(rest: str) -> str:
    """The heading words after a section number: 'Minimum Annual Royalties: Company...' -> 'Minimum Annual Royalties'."""
    run: list[str] = []
    for w in rest.split():
        bare = w.strip("\"'(),")
        if not bare or re.match(r"^\d", w) or re.match(r"^[A-Z]\.$", w):
            break
        if not (bare[0].isupper() or bare.lower() in SMALL_WORDS):
            # A capitalized word right before body text opens the sentence, not the title.
            while run and run[-1].lower() in SMALL_WORDS:
                run.pop()
            if run and not run[-1].endswith((".", ":", ",", '"')) and (len(run) == 1 or not run[-1].strip("\"'(),").isupper()):
                run.pop()
            break
        if run and run[0].isupper() and not bare.isupper() and bare.lower() not in SMALL_WORDS:
            break  # an ALLCAPS title ends where Title-case body begins
        run.append(w)
        if w[-1] in ".:;" or len(run) == 8:
            break
    while run and run[-1].lower() in SMALL_WORDS:
        run.pop()
    if run and run[0] in SENTENCE_OPENERS:
        return ""
    return " ".join(run).rstrip(".:;,")


def heading_of(p: str, parent: str) -> str:
    if is_caps_heading(p):
        return p
    if ANNEX.match(p):
        return " ".join(p.split()[:6])
    m = re.match(r"^((?:Section\s+)?\d{1,2}(?:\.\d{1,2})*\.?)\s+(.*)$", p)
    if not m:
        return " ".join(p.split()[:6])
    title = title_run(m.group(2))
    if title:
        return f"{m.group(1)} {title}"
    return f"{m.group(1)} ({parent})" if parent else m.group(1)


def is_heading_only(paras: list[str]) -> bool:
    """True while a clause holds only titles ('3. FEES', 'RECITALS'), so the next section joins it."""

    def bare(p: str) -> bool:
        rest = re.sub(r"^(?:Section\s+)?[\d.]+\s+", "", p) if SECTION.match(p) else None
        return rest is not None and title_run(rest) == rest.rstrip(".:;, ")

    return all(is_caps_heading(p) or bare(p) or (ANNEX.match(p) and len(p) <= 70) for p in paras)


def group(paras: list[str], subitem: str | None) -> list[tuple[str, list[str]]]:
    sub = re.compile(subitem) if subitem else None
    clauses: list[tuple[str, list[str]]] = []
    parent, in_signature = "", False
    for p in paras:
        if ANNEX.match(p):
            in_signature = False
        section = SECTION.match(p) and not (sub and sub.match(p))
        if SIGNATURE.match(p):
            in_signature, starts = True, True
        elif in_signature:
            starts = bool(ANNEX.match(p))
        else:
            starts = bool(section or is_caps_heading(p) or ANNEX.match(p))
        head = "Signatures" if SIGNATURE.match(p) else heading_of(p, parent)
        if section and re.match(r"^(?:Section\s+)?\d{1,2}\.?\s", p):
            parent = title_run(re.sub(r"^(?:Section\s+)?\d{1,2}\.?\s+", "", p))
        if clauses and (not starts or is_heading_only(clauses[-1][1])):
            clauses[-1][1].append(p)
        else:
            clauses.append((head, [p]))
    return clauses


def chunks(paras: list[str]) -> list[str]:
    """Pack paragraphs into pieces under MAX_CHARS; split oversized paragraphs at sentences."""
    units: list[tuple[str, str]] = []
    for p in paras:
        if len(p) <= MAX_CHARS:
            units.append(("\n", p))
        else:
            sentences = [s for s in re.split(r"(?<=[.;])\s+(?=[A-Z(])", p) if s]
            units.extend(("\n" if i == 0 else " ", s) for i, s in enumerate(sentences))
    out: list[str] = []
    for sep, u in units:
        # ponytail: a single sentence over MAX_CHARS stays whole; none exist in these six contracts.
        if out and len(out[-1]) + 1 + len(u) <= MAX_CHARS:
            out[-1] += sep + u
        else:
            out.append(u)
    return out


def split_contract(texts: list[str], source: Source = Source(())) -> list[dict]:
    clauses: list[dict] = []
    for text in texts:
        for head, paras in group(paragraphs(text, source.strip), source.subitem):
            for i, part in enumerate(chunks(paras)):
                h = head if i == 0 else f"{head} (cont. {i + 1})"
                clauses.append({"id": f"c-{len(clauses) + 1:03d}", "heading": h, "text": part})
    return clauses


def build(case_id: str, cuad_dir: Path) -> dict:
    source = CASES[case_id]
    texts = [(cuad_dir / f).read_text(encoding="utf-8", errors="replace") for f in source.files]
    path = CASES_DIR / case_id / "case.json"
    meta = json.loads(path.read_text()) if path.exists() else {}
    case = {
        "id": case_id,
        "title": meta.get("title", ""),
        "contract_type": meta.get("contract_type", ""),
        "reporting_entity": meta.get("reporting_entity", ""),
        "customer": meta.get("customer", ""),
        "why_hard": meta.get("why_hard", ""),
        "source": meta.get("source", " + ".join(source.files)),
        "clauses": split_contract(texts, source),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(case, indent=2, ensure_ascii=False) + "\n")
    return case


def _selfcheck() -> None:
    text = (
        "3. FEES\n3.01. You pay a fee.\n4. GRANT 4.1 License: Licensor grants a license. "
        "4.2 Royalty: Pay 4%.\ncontinued here.\n12\nSource: X, 10-K\n4.3 Company shall report.\n"
        "IN WITNESS WHEREOF the parties sign.\nACME, INC.\nEXHIBIT A FEES\n1. LICENSE FEE is $2000."
    )
    got = split_contract([text])
    heads = [c["heading"] for c in got]
    assert heads == ["3. FEES", "4. GRANT", "4.2 Royalty", "4.3 (GRANT)", "Signatures", "EXHIBIT A FEES"], heads
    assert got[2]["text"] == "4.2 Royalty: Pay 4%. continued here.", got[2]
    assert got[4]["text"].endswith("ACME, INC."), got[4]
    long = "3. Big. " + " ".join(["A sentence here."] * 400)
    assert all(len(c["text"]) <= MAX_CHARS for c in split_contract([long]))


if __name__ == "__main__":
    _selfcheck()
    cuad = Path(sys.argv[1])
    for cid in CASES:
        case = build(cid, cuad)
        print(f"\n== {cid}: {len(case['clauses'])} clauses")
        for c in case["clauses"]:
            print(f"{c['id']} | {len(c['text']):5d} | {c['heading'][:70]}")
