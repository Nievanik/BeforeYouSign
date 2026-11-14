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
