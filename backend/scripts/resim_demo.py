"""Re-run only the simulation on the saved demo datasets (no API calls: sites, competitors and Census come from the file).

    cd backend && .venv/bin/python -m scripts.resim_demo            # both datasets
    cd backend && .venv/bin/python -m scripts.resim_demo salon      # just one

Use after changing app/sim. The agent's report text is not regenerated, so odds it quotes may be stale.
"""
import json
import sys

from app import config, sim
from app.models import Site
from scripts.record_demo import DATASETS


TYPICAL_MARGIN = 0.10


def profile_for(business_type: str, saved: dict) -> dict:
    """The preset from config when there is one; else the run's saved AI estimate, with other fixed costs raised so
    a typical shop nets ~10% (what the profile prompt now asks the LLM for; re-asking it would call the API)."""
    if business_type in config.BUSINESS_PROFILES:
        return config.BUSINESS_PROFILES[business_type]
    # a rate from "hot and new" shops is saved in place of the profile's; simulate recomputes it either way
    p = {k: saved[k] for k in sim.PROFILE_FIELDS}
    revenue = p["typicalDailyCustomers"] * p["ticket"] * p["daysOpen"]
    profit = (revenue * (1 - (p["cogsMin"] + p["cogsMax"]) / 2 - p["laborVariablePct"]) - p["laborFixedMonthly"]
              - p["otherFixedMonthly"] - 0.10 * revenue)  # rent at 10% of revenue
    p["otherFixedMonthly"] += max(0.0, round(profit - TYPICAL_MARGIN * revenue, -2))
    return p


def resim(name: str) -> None:
    path = config.DEMO_DIR / f"{name}.json"
    data = json.loads(path.read_text())
    new = {}
    for s in data["result"]["sites"]:
        if not s.get("sim"):
            continue
        profile = profile_for(data["result"]["brief"]["businessType"], s["sim"]["assumptions"])
        site = Site(**{**s, "sim": None})
        new[s["id"]] = sim.simulate(site, profile).model_dump()
        print(f"  {s['id']}: {s['sim']['pProfitableBy12']:.0%} -> {new[s['id']]['pProfitableBy12']:.0%}")
        s["sim"] = new[s["id"]]

    for _, kind, d in data["events"]:
        if kind == "sim" and d["siteId"] in new:
            d["result"] = new[d["siteId"]]
        elif kind == "site" and d.get("sim") and d["id"] in new:
            d["sim"] = new[d["id"]]

    # same order rule as agent.run.ranked: the agent's picks first, then the other simulated sites by odds
    picks = next((d["siteIds"] for _, kind, d in data["events"] if kind == "ranking"), [])
    sites = data["result"]["sites"]
    first = [s for i in picks for s in sites if s["id"] == i]
    rest = sorted((s for s in sites if s["id"] not in picks and s.get("sim")),
                  key=lambda s: s["sim"]["pProfitableBy12"], reverse=True)
    data["result"]["sites"] = first + rest + [s for s in sites if s["id"] not in picks and not s.get("sim")]

    path.write_text(json.dumps(data))
    print(f"saved {path}")


if __name__ == "__main__":
    for name in sys.argv[1:] or DATASETS:
        print(f"== {name}")
        resim(name)
