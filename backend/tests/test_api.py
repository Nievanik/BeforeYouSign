from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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
