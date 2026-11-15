"""Re-run only the simulation on the saved demo datasets (no API calls: sites, competitors and Census come from the file).

    cd backend && .venv/bin/python -m scripts.resim_demo            # both datasets
    cd backend && .venv/bin/python -m scripts.resim_demo salon      # just one

Use after changing app/sim. The report is rewritten from the new numbers (the agent's text quoted the old ones).
"""
import ast
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


def _what_if(data: dict) -> str | None:
    """Redo the agent's what-if experiment ("What-if on <id>: {...}") with the current simulation."""
    msg = next((d["message"] for _, kind, d in data["events"]
                if kind == "step" and d.get("status") == "done" and d.get("message", "").startswith("What-if on ")), None)
    if not msg:
        return None
    site_id, overrides = msg.removeprefix("What-if on ").split(": ", 1)
    overrides = ast.literal_eval(overrides)
    s = next((s for s in data["result"]["sites"] if s["id"] == site_id and s.get("sim")), None)
    if not s or set(overrides) - sim.OVERRIDE_KEYS:
        return None
    profile = profile_for(data["result"]["brief"]["businessType"], s["sim"]["assumptions"])
    after = sim.simulate(Site(**{**s, "sim": None}), profile, overrides).pProfitableBy12
    labels = {"newCompetitors": "new competitor openings", "accessPenalty": "the road-access handicap"}
    what = ", ".join(f"switching off {labels[k]}" if v is False and k in labels else f"{k} = {v}"
                     for k, v in overrides.items())
    return (f"**What-if (agent's investigation):** on {s['address']}, {what} moves the odds from "
            f"{s['sim']['pProfitableBy12']:.0%} to {after:.0%}.")


def report(data: dict, picks: list[dict], rest: list[dict]) -> str:
    """Markdown report built only from the saved evidence and the current simulation numbers."""
    b = data["result"]["brief"]
    lines = [f"## {b['businessType'].title()} sites in {b['city']}", "",
             f"The agent shortlisted {len(data['result']['sites'])} CoStar listings and inspected its top "
             f"{len(picks)} picks in depth (aerial photo, 3D scan). Odds come from 1,000 simulated futures per site.", ""]
    for i, s in enumerate(picks, 1):
        m, a, it = s["sim"], s.get("aerial") or {}, s.get("interior") or {}
        comps = sum(c["kind"] == "competitor" for c in s["competitors"])
        lines.append(f"**{i}. {s['address']}**: {m['pProfitableBy12']:.0%} chance of profit by month 12")
        lines.append(f"- Rent ${s['rentMonthly']:,.0f}/mo, {s['sizeSqft']:,.0f} sq ft"
                     + (f", {s['parkingSpaces']:,} parking spaces" if s.get("parkingSpaces") else ""))
        lines.append(f"- ~{m['expectedCustomers']:.0f} customers/day expected vs {m['breakEvenCustomers']:.0f} needed; "
                     f"rent is {m['rentShare']:.0%} of revenue; {comps} competitors nearby")
        if a.get("visibilityScore"):
            lines.append(f"- Aerial: visibility {a['visibilityScore']}/5 ({a['visibilityReason']}), "
                         f"road access {a['roadAccessScore']}/5 ({a['roadAccessReason']})")
        if it:
            lines.append(f"- Inside: {it['floorAreaSqft']:,.0f} sq ft scanned, ~{it['estSeats']} seats")
        if m["riskFactors"]:
            lines.append(f"- Main risk: {m['riskFactors'][0]['text']}")
        if s["gaps"]:
            lines.append(f"- Data gaps: {'; '.join(s['gaps'])}")
        lines.append("")
    if w := _what_if(data):
        lines += [w, ""]
    if rest:
        lines += ["### Other candidates (simulated, not inspected)",
                  *(f"- {s['address']}: {s['sim']['pProfitableBy12']:.0%}, ${s['rentMonthly']:,.0f}/mo" for s in rest), ""]
    lines.append("_Compare sites with these odds; the dollar figures rest on benchmark assumptions._")
    return "\n".join(lines)


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

    # the agent's picks first, then the other simulated sites; each group by the new odds (the agent's own
    # order was based on the old numbers)
    picks = next((d["siteIds"] for _, kind, d in data["events"] if kind == "ranking"), [])
    sites = data["result"]["sites"]
    odds = lambda s: s["sim"]["pProfitableBy12"]
    first = sorted((s for i in picks for s in sites if s["id"] == i and s.get("sim")), key=odds, reverse=True)
    rest = sorted((s for s in sites if s["id"] not in picks and s.get("sim")), key=odds, reverse=True)
    data["result"]["sites"] = first + rest + [s for s in sites if s not in first and s not in rest]

    # the agent's report quoted the old numbers: rewrite it from the new ones
    md = report(data, first, rest)
    data["result"]["report"] = md
    for _, kind, d in data["events"]:
        if kind == "report":
            d["markdown"] = md

    path.write_text(json.dumps(data))
    print(f"saved {path}")


if __name__ == "__main__":
    for name in sys.argv[1:] or DATASETS:
        print(f"== {name}")
        resim(name)
