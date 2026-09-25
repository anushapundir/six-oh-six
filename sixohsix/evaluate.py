"""Run a runner over cases, score each, and persist results plus the scoreboard."""

import json
import os
import threading
from concurrent.futures import ThreadPoolExecutor
from statistics import mean
from typing import Literal

from pydantic import TypeAdapter

from sixohsix import agent, baseline
from sixohsix.cases import data_root
from sixohsix.schema import Case, Reference, Result
from sixohsix.score import score

Runner = Literal["baseline", "agent"]
RUNNERS: tuple[Runner, ...] = ("baseline", "agent")
SCORE_FIELDS = ("obligation_f1", "timing_accuracy", "consideration_correct", "grounding", "overall")
Results = TypeAdapter(list[Result])
# Guards the read-merge-write of results files. In-process only.
_write = threading.Lock()


def results_path(runner: Runner):
    return data_root() / "results" / f"{runner}.json"


def load_results(runner: Runner) -> list[Result]:
    p = results_path(runner)
    return Results.validate_json(p.read_bytes()) if p.exists() else []


def run_one(runner: Runner, case: Case, ref: Reference, on_step=None) -> Result:
    if runner == "baseline":
        analysis = baseline.analyze(case)
        return Result(case_id=case.id, runner=runner, analysis=analysis, scores=score(analysis, ref, case))
    analysis, trace, usage, seconds = agent.analyze(case, on_step=on_step)
    return Result(
        case_id=case.id,
        runner=runner,
        analysis=analysis,
        scores=score(analysis, ref, case),
        trace=trace,
        model=agent.model(),
        # Total prompt tokens, cached or not.
        input_tokens=usage["input_tokens"] + usage["cache_read_input_tokens"] + usage["cache_creation_input_tokens"],
        output_tokens=usage["output_tokens"],
        seconds=round(seconds, 1),
    )


def run(runner: Runner, cases: list[tuple[Case, Reference]], only: str | None = None) -> list[Result]:
    todo = [(c, r) for c, r in cases if only in (None, c.id)]

    def attempt(cr: tuple[Case, Reference]) -> Result | None:
        try:
            return run_one(runner, *cr)
        except Exception as e:  # one failed case shouldn't sink the run
            print(f"  {runner} {cr[0].id}: failed: {e}")
            return None

    with ThreadPoolExecutor(max_workers=4 if runner == "agent" else 1) as pool:
        fresh = [r for r in pool.map(attempt, todo) if r]

    merge(runner, fresh, {c.id for c, _ in cases})
    return fresh


def merge(runner: Runner, fresh: list[Result], ids: set[str]) -> None:
    """Keep earlier results for cases not rerun; drop results for cases that no longer exist."""
    rerun = {r.case_id for r in fresh}
    with _write:
        merged = [r for r in load_results(runner) if r.case_id in ids and r.case_id not in rerun] + fresh
        save(runner, sorted(merged, key=lambda r: r.case_id))


def save(runner: Runner, results: list[Result]) -> None:
    p = results_path(runner)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(Results.dump_json(results, indent=2))
    write_scoreboard()


def write_scoreboard() -> dict:
    board: dict = {"runners": {}, "cases": {}}
    for runner in RUNNERS:
        results = load_results(runner)
        if not results:
            continue
        board["runners"][runner] = {
            **{f: round(mean(getattr(r.scores, f) for r in results), 3) for f in SCORE_FIELDS},
            "cases": len(results),
            "input_tokens": sum(r.input_tokens for r in results),
            "output_tokens": sum(r.output_tokens for r in results),
            "seconds": round(sum(r.seconds for r in results), 1),
        }
        for r in results:
            board["cases"].setdefault(r.case_id, {})[runner] = round(r.scores.overall, 3)
    (data_root() / "scoreboard.json").write_text(json.dumps(board, indent=2))
    return board


def has_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))
