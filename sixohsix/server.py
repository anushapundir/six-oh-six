import json
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from sixohsix import evaluate, memo
from sixohsix.cases import REPO, data_root, load_cases
from sixohsix.schema import KINDS, Case, Reference

load_dotenv(REPO / ".env")
WEB = Path(__file__).parent / "web"

app = FastAPI(title="six-oh-six")
app.mount("/static", StaticFiles(directory=WEB), name="static")


def find(case_id: str) -> tuple[Case, Reference]:
    for case, ref in load_cases():
        if case.id == case_id:
            return case, ref
    raise HTTPException(404, f"No case {case_id!r}")


def results_by_case(runner: evaluate.Runner) -> dict:
    return {r.case_id: r for r in evaluate.load_results(runner)}


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/cases")
def cases():
    results = {runner: results_by_case(runner) for runner in evaluate.RUNNERS}
    return [
        {
            "id": c.id,
            "title": c.title,
            "why_hard": c.why_hard,
            "overall": {rn: (res[c.id].scores.overall if c.id in res else None) for rn, res in results.items()},
        }
        for c, _ in load_cases()
    ]


@app.get("/api/cases/{case_id}")
def case_detail(case_id: str):
    case, ref = find(case_id)
    return {
        "case": case,
        "reference": ref,
        "results": {rn: results_by_case(rn).get(case_id) for rn in evaluate.RUNNERS},
        "kinds": {k.value: info.label for k, info in KINDS.items()},
        "can_run": evaluate.has_key(),
    }


@app.get("/api/scoreboard")
def scoreboard():
    p = data_root() / "scoreboard.json"
    return json.loads(p.read_text()) if p.exists() else evaluate.write_scoreboard()


@app.get("/api/cases/{case_id}/memo.docx")
def memo_docx(case_id: str, runner: Literal["agent", "baseline"] = "agent"):
    case, _ = find(case_id)
    result = results_by_case(runner).get(case_id)
    if result is None:
        raise HTTPException(404, f"No {runner} result for {case_id}. Run it first.")
    return Response(
        memo.render(case, result.analysis),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{case_id}-{runner}-memo.docx"'},
    )


@app.post("/api/cases/{case_id}/run")
def run_agent(case_id: str):
    find(case_id)
    if not evaluate.has_key():
        raise HTTPException(409, "ANTHROPIC_API_KEY is not set on the server, so the agent can't run. Add it to .env and restart.")
    fresh = evaluate.run("agent", load_cases(), only=case_id)
    if not fresh:
        raise HTTPException(502, "The agent run failed. Check the server log.")
    return fresh[0]
