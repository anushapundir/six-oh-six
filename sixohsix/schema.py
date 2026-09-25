"""The data every part of six-oh-six speaks: contracts in, revenue analyses out."""

from enum import StrEnum
from typing import Literal, NamedTuple

from pydantic import BaseModel, Field


class Timing(StrEnum):
    POINT_IN_TIME = "point_in_time"
    OVER_TIME = "over_time"


class Kind(StrEnum):
    SAAS = "saas"
    LICENSE_FUNCTIONAL = "license_functional"
    LICENSE_SYMBOLIC = "license_symbolic"
    SUPPORT = "support"
    SERVICES = "services"
    GOODS = "goods"


class KindInfo(NamedTuple):
    label: str
    usual_timing: Timing
    guidance: tuple[str, ...]


# One row per kind of promise. UI labels, the baseline, and the memo all read this table.
KINDS: dict[Kind, KindInfo] = {
    Kind.SAAS: KindInfo("Hosted software access", Timing.OVER_TIME, ("606-10-55-54", "606-10-25-27")),
    Kind.LICENSE_FUNCTIONAL: KindInfo("License to use IP as it exists", Timing.POINT_IN_TIME, ("606-10-55-58", "606-10-55-62")),
    Kind.LICENSE_SYMBOLIC: KindInfo("License to access IP over time", Timing.OVER_TIME, ("606-10-55-59", "606-10-55-60")),
    Kind.SUPPORT: KindInfo("Support, maintenance and updates", Timing.OVER_TIME, ("606-10-25-14", "606-10-25-27")),
    Kind.SERVICES: KindInfo("Services (implementation, development, consulting)", Timing.OVER_TIME, ("606-10-25-27", "606-10-25-30")),
    Kind.GOODS: KindInfo("Physical goods", Timing.POINT_IN_TIME, ("606-10-25-30",)),
}


class Clause(BaseModel):
    id: str = Field(description="Stable id, e.g. 'c-014'. Citations point here.")
    heading: str
    text: str


class Case(BaseModel):
    id: str
    title: str
    contract_type: str
    reporting_entity: str = Field(description="The seller whose revenue we analyze.")
    customer: str
    why_hard: str = Field(description="One line: the judgment call that trips people up.")
    source: str = Field(description="CUAD file name or EDGAR URL.")
    clauses: list[Clause]


class Obligation(BaseModel):
    kind: Kind
    description: str
    timing: Timing
    rationale: str
    clauses: list[str] = Field(description="Clause ids this conclusion rests on.")
    guidance: list[str] = Field(default_factory=list, description="ASC paragraph refs, e.g. '606-10-55-58'.")


class Consideration(BaseModel):
    summary: str
    variable: bool = Field(description="Any usage, royalty, milestone, rebate or penalty terms.")
    royalty_exception: bool = Field(description="Sales- or usage-based royalty on an IP license (606-10-55-65).")
    rationale: str
    clauses: list[str]


class Analysis(BaseModel):
    """What a runner (baseline or agent) concludes about one contract."""

    reporting_entity: str
    summary: str
    obligations: list[Obligation]
    consideration: Consideration
    open_questions: list[str] = Field(default_factory=list, description="Judgment calls a human should make.")


class RefObligation(BaseModel):
    kind: Kind
    timing: Timing
    clauses: list[str]
    rationale: str


class Reference(BaseModel):
    """Hand labels for one case. Draft until a human signs off."""

    status: Literal["draft", "reviewed"] = "draft"
    obligations: list[RefObligation]
    variable: bool
    royalty_exception: bool
    rationale: str
    clauses: list[str]


class Step(BaseModel):
    tool: str
    input: dict
    output: str


class Scores(BaseModel):
    obligation_f1: float
    timing_accuracy: float
    consideration_correct: float
    grounding: float = Field(description="Share of cited clause ids that exist in the contract.")
    hallucinated: list[str]
    overall: float


class Result(BaseModel):
    case_id: str
    runner: Literal["baseline", "agent"]
    analysis: Analysis
    scores: Scores
    trace: list[Step] = Field(default_factory=list)
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    seconds: float = 0.0
