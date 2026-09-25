import shutil
import threading
import time
from pathlib import Path

from fastapi.testclient import TestClient

from sixohsix import baseline, evaluate, server
from sixohsix.schema import Result, Step
from sixohsix.score import score

FIXTURES = Path(__file__).parent / "fixtures"


def test_run_returns_at_once_and_reports_progress(tmp_path, monkeypatch):
    shutil.copytree(FIXTURES / "cases", tmp_path / "cases")
    monkeypatch.setenv("SIXOHSIX_DATA", str(tmp_path))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    release = threading.Event()

    def fake_run_one(runner, case, ref, on_step=None):
        on_step(Step(tool="read_clause", input={"clause_id": "c-001"}, output=""))
        release.wait(5)
        analysis = baseline.analyze(case)
        return Result(case_id=case.id, runner=runner, analysis=analysis, scores=score(analysis, ref, case))

    monkeypatch.setattr(evaluate, "run_one", fake_run_one)
    client = TestClient(server.app)
    url = "/api/cases/fx-onprem-royalty/run"

    assert client.get(url).json()["status"] == "idle"
    assert client.post(url).status_code == 202
    assert client.post(url).status_code == 409
    running = client.get(url).json()
    assert running["status"] == "running"
    assert running["steps"] == ["read_clause(c-001)"]

    release.set()
    for _ in range(50):
        if client.get(url).json()["status"] == "done":
            break
        time.sleep(0.05)
    assert client.get(url).json()["status"] == "done"
    assert [r.case_id for r in evaluate.load_results("agent")] == ["fx-onprem-royalty"]


def test_run_without_key_is_refused(tmp_path, monkeypatch):
    monkeypatch.setenv("SIXOHSIX_DATA", str(FIXTURES))
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert TestClient(server.app).post("/api/cases/fx-onprem-royalty/run").status_code == 409
