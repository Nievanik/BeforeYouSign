import pytest
from fastapi.testclient import TestClient

from app import cache
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def tmp_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "CACHE_DIR", tmp_path)  # recorded runs must never land in the real cache
    from app import main

    def no_llm(q):
        raise RuntimeError("no LLM in tests")

    monkeypatch.setattr(main, "parse_brief", no_llm)  # tests use the keyword fallback unless they patch this


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


def test_analyze_endpoint_starts_run():
    resp = client.post("/api/analyze", json={"query": "Boba shop in Houston, max $6k/month rent"})
    assert resp.status_code == 202
    data = resp.json()
    assert "runId" in data
    assert data["brief"]["businessType"] == "boba"
    assert data["brief"]["city"] == "Houston"


def test_analyze_streams_events_then_stores_result(monkeypatch):
    from app import main
    from app.models import BusinessBrief

    def fake_agent(query, emit, brief=None):
        b = brief or BusinessBrief(businessType="boba", city="Houston", maxRentMonthly=6000)
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
def test_simulate_site_with_overrides():
    site = client.get("/api/runs/golden").json()["sites"][0]
    # base simulation
    res1 = client.post("/api/simulate", json={"site": site, "businessType": "boba", "overrides": {}}).json()
    assert 0 <= res1["pProfitableBy12"] <= 1
    assert len(res1["monthlyBands"]) == 24
    # what-if override with lower rent and higher ticket
    res2 = client.post("/api/simulate", json={
        "site": site,
        "businessType": "boba",
        "overrides": {"rentMonthly": 2000, "ticket": 12.0}
    }).json()
    assert res2["pProfitableBy12"] >= res1["pProfitableBy12"]


def test_what_if_keeps_the_sites_own_business_numbers():
    """The What-If panel sends businessType "boba" for every site: a simulated salon must stay a salon."""
    from app import config, sim
    from app.models import Site
    site = Site(**client.get("/api/runs/golden").json()["sites"][0])
    site.sim = sim.simulate(site, config.BUSINESS_PROFILES["salon"])
    res = client.post("/api/simulate", json={"site": site.model_dump(), "businessType": "boba", "overrides": {}}).json()
    assert res["pProfitableBy12"] == site.sim.pProfitableBy12
    assert res["assumptions"]["typicalDailyCustomers"] == 25


def test_analyze_uses_llm_brief_when_available(monkeypatch):
    from app import main
    from app.models import BusinessBrief

    llm = BusinessBrief(businessType="nail salon", city="Houston", maxRentMonthly=4000)
    monkeypatch.setattr(main, "parse_brief", lambda q: llm)
    monkeypatch.setattr(main, "run_agent", lambda q, emit, brief=None: (_ for _ in ()).throw(RuntimeError("stop")))
    data = client.post("/api/analyze", json={"query": "nail salon under 4k"}).json()
    assert data["brief"]["businessType"] == "nail salon" and data["brief"]["sizeSqftMin"] is None


def test_keyword_fallback_does_not_invent_sizes():
    data = client.post("/api/analyze", json={"query": "Hair salon in Houston"}).json()
    assert data["brief"]["businessType"] == "salon"
    assert data["brief"]["sizeSqftMin"] is None and data["brief"]["sizeSqftMax"] is None


def test_simulate_a_candidate_the_agent_skipped():
    import json
    from pathlib import Path
    from app import main
    from app.models import RunResult

    golden = json.loads((Path(__file__).parents[1] / "fixtures" / "golden_run.json").read_text())
    golden["sites"][2]["sim"] = None
    main.RUNS["r_test"] = {"events": [], "result": RunResult(**{**golden, "runId": "r_test"})}
    sid = golden["sites"][2]["id"]
    site = client.post(f"/api/runs/r_test/sites/{sid}/simulate").json()
    assert 0 <= site["sim"]["pProfitableBy12"] <= 1
    assert client.get("/api/runs/r_test").json()["sites"][2]["sim"] is not None  # stored, survives a reload
    assert client.post("/api/runs/r_test/sites/nope/simulate").status_code == 404
    assert client.post("/api/runs/nope/sites/x/simulate").status_code == 404


def test_keyword_fallback_reads_size_rent_and_parking():
    from app.main import parse_query_to_brief

    b = parse_query_to_brief("Boba shop in Houston, max $6k/month rent, at least 1000 sq ft, needs parking")
    assert (b.maxRentMonthly, b.sizeSqftMin, b.parkingRequired) == (6000, 1000, True)
    b = parse_query_to_brief("Hair salon, max $5,500/month, 1000-1500 sq ft")
    assert (b.maxRentMonthly, b.sizeSqftMin, b.sizeSqftMax, b.parkingRequired) == (5500, 1000, 1500, False)
