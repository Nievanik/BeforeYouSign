"""Tests for the deterministic fallback pipeline (Dev 2 Hours 4.5–6)."""
from app import config
from app.agent.pipeline import run_pipeline
from app.models import BusinessBrief, RunResult


def test_run_pipeline_end_to_end(monkeypatch):
    monkeypatch.setattr(config, "OFFLINE", True)
    brief = BusinessBrief(
        businessType="boba",
        city="Houston",
        maxRentMonthly=6000,
        sizeSqftMin=800,
        sizeSqftMax=2000,
        mustHaves=["parking"],
    )

    events: list[tuple[str, dict]] = []

    def handle_event(name: str, data: dict):
        events.append((name, data))

    result = run_pipeline(brief, max_sites=2, on_event=handle_event)

    assert isinstance(result, RunResult)
    assert result.brief.businessType == "boba"
    assert len(result.sites) > 0
    assert len(result.sites) <= 2
    assert len(result.report) > 0

    # Verify site structure and risk factors
    for s in result.sites:
        assert s.sim is not None
        assert 0.0 <= s.sim.pProfitableBy12 <= 1.0
        assert len(s.sim.riskFactors) <= 3
        for r in s.sim.riskFactors:
            assert r.factor in {"competitors", "rent", "customers", "workers", "visibility", "access", "new_competitors"}
            assert len(r.text) > 0

    # Verify event stream
    event_names = [e[0] for e in events]
    assert "brief" in event_names
    assert "step" in event_names
    assert "site" in event_names
    assert "sim" in event_names
    assert "report" in event_names
    assert "done" in event_names
