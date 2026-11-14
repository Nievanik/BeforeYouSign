import pytest
from fastapi.testclient import TestClient

from app import cache
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)  # recorded runs must never land in the real cache


def test_health():
    assert client.get("/api/health").json()["ok"] is True


def test_golden_run_matches_contract():
    r = client.get("/api/runs/golden")  # response_model validates against models.RunResult
    assert r.status_code == 200
    sites = r.json()["sites"]
    assert len(sites) == 3
    odds = [s["sim"]["pProfitableBy12"] for s in sites]
    assert odds == sorted(odds, reverse=True), "sites must be ranked by odds"


def test_unknown_run_404():
    assert client.get("/api/runs/nope").status_code == 404


def test_analyze_streams_events_then_stores_result(monkeypatch):
    from app import main
    from app.models import BusinessBrief

    def fake_agent(query, emit, brief=None):
        b = BusinessBrief(businessType="boba", city="Houston", maxRentMonthly=6000)
        emit("brief", b.model_dump())
        emit("report", {"markdown": "pick A"})
        return type("R", (), {"brief": b, "report": "pick A", "sites": {}, "ranking": []})()

    monkeypatch.setattr(main, "run_agent", fake_agent)
    assert client.post("/api/analyze", json={"query": " "}).status_code == 400
    run_id = client.post("/api/analyze", json={"query": "boba in Houston"}).json()["runId"]
    body = client.get(f"/api/runs/{run_id}/events").text
    assert [l[7:] for l in body.splitlines() if l.startswith("event: ")] == ["brief", "report", "done"]
    assert client.get(f"/api/runs/{run_id}").json()["report"] == "pick A"


def test_agent_failure_is_fatal_error_then_done(monkeypatch):
    from app import main

    monkeypatch.setattr(main, "run_agent", lambda *a: 1 / 0)
    run_id = client.post("/api/analyze", json={"query": "boba"}).json()["runId"]
    body = client.get(f"/api/runs/{run_id}/events").text
    assert "event: error" in body and '"fatal":true' in body.replace(" ", "") and "event: done" in body
    assert client.get(f"/api/runs/{run_id}").status_code == 409


def test_offline_replays_a_recorded_run(monkeypatch, tmp_path):
    from app import config, main
    from app.models import BusinessBrief

    monkeypatch.setattr(main, "MAX_REPLAY_GAP_S", 0)
    b = BusinessBrief(businessType="boba", city="Houston", maxRentMonthly=6000)

    def fake_agent(query, emit, brief=None):
        emit("brief", b.model_dump())
        emit("plan", {"todos": []})
        return type("R", (), {"brief": b, "report": "live", "sites": {}, "ranking": []})()

    monkeypatch.setattr(main, "run_agent", fake_agent)
    client.get(f"/api/runs/{client.post('/api/analyze', json={'query': 'Boba'}).json()['runId']}/events")

    monkeypatch.setattr(config, "OFFLINE", True)
    monkeypatch.setattr(main, "run_agent", lambda *a: 1 / 0)  # must not be called offline
    run_id = client.post("/api/analyze", json={"query": " boba "}).json()["runId"]
    body = client.get(f"/api/runs/{run_id}/events").text
    assert [l[7:] for l in body.splitlines() if l.startswith("event: ")] == ["brief", "plan", "done"]
    assert client.get(f"/api/runs/{run_id}").json()["runId"] == run_id


def test_auto_mode_run_is_not_recorded(monkeypatch, tmp_path):
    from app import main
    from app.models import BusinessBrief

    b = BusinessBrief(businessType="boba", city="Houston", maxRentMonthly=6000)

    def fake_agent(query, emit, brief=None):
        emit("step", {"id": "fallback", "tool": "pipeline", "siteId": None, "status": "running", "message": "429"})
        return type("R", (), {"brief": b, "report": "auto", "sites": {}, "ranking": []})()

    monkeypatch.setattr(main, "run_agent", fake_agent)
    client.get(f"/api/runs/{client.post('/api/analyze', json={'query': 'boba'}).json()['runId']}/events")
    assert not (tmp_path / "runs").exists()
