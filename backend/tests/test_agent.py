import pytest

from app.agent import run as agent_run
from app.models import BusinessBrief
from tests.test_sim import BOBA


@pytest.fixture
def run(monkeypatch):
    monkeypatch.setattr(agent_run, "profile_for", lambda t: (BOBA, False))
    events = []
    r = agent_run.Run(BusinessBrief(businessType="boba", city="Houston", maxRentMonthly=6000), lambda e, d: events.append((e, d)))
    r.events = events
    return r


def tool(run, name):
    return next(t for t in run.tools() if t.__name__ == name)


def test_budget_stops_the_agent(run):
    run.calls = agent_run.MAX_TOOL_CALLS
    with pytest.raises(agent_run.OverBudget):
        run.step("x", "msg", None, lambda: "ok")


def test_tool_error_becomes_text_not_crash(run):
    assert tool(run, "simulate")("nope").startswith("error: unknown site id")
    assert [d["status"] for e, d in run.events if e == "step"] == ["running", "error"]


def test_relax_rent_raises_limit_15_percent(run):
    tool(run, "relax_constraint")("rent", "only 3 sites")
    assert run.brief.maxRentMonthly == 6900
    assert ("brief", run.brief.model_dump()) in run.events


def test_pipeline_simulates_and_ranks_existing_sites(run):
    import json
    from pathlib import Path
    from app.agent import pipeline
    from app.models import Site

    golden = json.loads((Path(__file__).parents[1] / "fixtures" / "golden_run.json").read_text())
    for d in golden["sites"]:
        s = Site(**{**d, "sim": None})
        run.sites[s.id] = s
    run.calls = agent_run.MAX_TOOL_CALLS  # the agent spent its budget; auto mode gets a fresh one
    pipeline.finish(run)
    odds = [run.sites[i].sim.pProfitableBy12 for i in run.ranking]
    assert len(odds) == len(golden["sites"]) and odds == sorted(odds, reverse=True)
    assert "auto mode" in run.report


def test_repeat_search_keeps_gathered_evidence(run, monkeypatch):
    import json
    from pathlib import Path
    from app.models import Site

    d = json.loads((Path(__file__).parents[1] / "fixtures" / "golden_run.json").read_text())["sites"][0]
    run.sites = {d["id"]: Site(**d)}
    monkeypatch.setattr(agent_run.costar, "find_candidates", lambda b: [Site(**{**d, "sim": None})])
    tool(run, "find_candidates")()
    assert run.sites[d["id"]].sim is not None


def _golden_sites(n):
    import json
    from pathlib import Path
    from app.models import Site

    base = json.loads((Path(__file__).parents[1] / "fixtures" / "golden_run.json").read_text())["sites"]
    return [Site(**{**base[i % len(base)], "id": f"X{i}", "rentMonthly": 2000 + i, "sim": None}) for i in range(n)]


def test_pipeline_simulates_only_top_cheapest(run):
    from app.agent import pipeline

    run.sites = {s.id: s for s in _golden_sites(5)}
    pipeline.finish(run)
    assert sorted(i for i, s in run.sites.items() if s.sim) == ["X0", "X1", "X2"]  # the 3 cheapest
    assert agent_run.ranked(run)[-2:] == [run.sites["X3"], run.sites["X4"]]  # unsimulated listed last
