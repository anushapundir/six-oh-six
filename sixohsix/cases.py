import os
from pathlib import Path

from sixohsix.schema import Case, Reference

REPO = Path(__file__).resolve().parents[1]


def data_root() -> Path:
    """Holds cases/, results/ and scoreboard.json. SIXOHSIX_DATA points it elsewhere, e.g. tests/fixtures."""
    return Path(os.environ.get("SIXOHSIX_DATA", REPO / "data"))


def load_cases(root: Path | None = None) -> list[tuple[Case, Reference]]:
    root = root or data_root() / "cases"
    out = []
    for d in sorted(p for p in root.iterdir() if (p / "case.json").exists()):
        case = Case.model_validate_json((d / "case.json").read_text())
        ref = Reference.model_validate_json((d / "reference.json").read_text())
        out.append((case, ref))
    return sorted(out, key=lambda cr: cr[0].id)
