"""The site-search agent: deepagents + OpenRouter, plain-Python tools, events streamed to the UI.

emit(event, data) receives every event in docs/api.md: brief, plan, step, site, sim, report, done, error.
"""
import json
import time
from typing import Callable

from deepagents import create_deep_agent

from app import sim
from app.agent.brief import parse_brief, profile_for
from app.llm import chat_model
from app.models import BusinessBrief, Site
from app.tools import census, costar, matterport, osm, vexcel, vision

# shortcut: 120 s in requirements.md is too tight with live Overpass/Vexcel on a cold cache; cached reruns are fast
MAX_TOOL_CALLS, MAX_SECONDS = 25, 240
SHORTLIST, THIN = 8, 5
TOP = 3  # sites the agent simulates; the user can simulate the rest from their cards
RENT_STEP, SIZE_STEP = 1.15, 0.25

SYSTEM = """You are a commercial real estate analyst helping a small-business owner pick where to lease.
Tools return short text; site ids look like "L123-S4". Work like this, and say WHY in one short sentence
before each tool call:
1. Plan first with write_todos.
2. find_candidates. If it reports fewer than {thin} sites, call relax_constraint ONCE (rent or size), say which and why.
3. Pick the {top} most promising sites from the list (rent well under the limit, size that fits, more workers
   nearby) and say why in one sentence. Run simulate on those {top} ONLY: each simulation is slow. The user can
   simulate the others later, so do not simulate them.
   people_nearby and competitors give more detail: use them only when investigating a site.
4. Run inspect_aerial and inspect_interior on your {top} simulated sites (expensive).
5. Investigate (REQUIRED, at least one before finish): for the lowest-odds or most surprising site, rerun simulate with one factor switched off
   (overrides {{"newCompetitors": false}}, {{"accessPenalty": false}} or a lower "rentMonthly") to find what drives it.
   Missing data: note the gap and move on.
6. Call finish with the ranking of your simulated sites (best first) and a short report that cites numbers for
   each pick and names the other candidates as "not simulated yet".
You have at most {max_calls} tool calls in total, so do not repeat calls."""


class OverBudget(Exception):
    """The agent used too many tool calls or too much time: hand over to the fixed pipeline."""


def attempt(site: Site, gap: str, fn):
    try:
        return fn()
    except Exception as e:  # one tool failing never kills the run; it becomes a named gap
        site.gaps.append(f"{gap}: {str(e)[:80]}")
        return None


class Run:
    def __init__(self, brief: BusinessBrief, emit: Callable[[str, dict], None]):
        self.brief, self.emit = brief, emit
        self.profile, self.ai_profile = profile_for(brief.businessType)
        self.sites: dict[str, Site] = {}
        self.calls, self.started, self.n = 0, time.monotonic(), 0
        self.ranking: list[str] = []
        self.report = ""

    # --- helpers -------------------------------------------------------------------------------------
    def step(self, tool: str, message: str, site_id: str | None, fn):
        """Count the call against the budget, stream running/done/error, return fn()'s text."""
        self.calls += 1
        if self.calls > MAX_TOOL_CALLS or time.monotonic() - self.started > MAX_SECONDS:
            raise OverBudget(f"{self.calls} tool calls, {time.monotonic() - self.started:.0f}s")
        self.n += 1
        sid = f"s{self.n}"
        self.emit("step", {"id": sid, "tool": tool, "siteId": site_id, "message": message, "status": "running"})
        try:
            out = fn()
        except OverBudget:
            raise
        except Exception as e:
            self.emit("step", {"id": sid, "tool": tool, "siteId": site_id, "message": f"{message}: {e}"[:200],
                               "status": "error"})
            return f"error: {e}"[:300]
        self.emit("step", {"id": sid, "tool": tool, "siteId": site_id, "message": message, "status": "done"})
        return out

    def site(self, site_id: str) -> Site:
        if site_id not in self.sites:
            raise ValueError(f"unknown site id {site_id!r}; use ids from find_candidates")
        return self.sites[site_id]

    def run_sim(self, s: Site, overrides: dict | None = None):
        if s.demographics is None and not any(g.startswith("no demographics") for g in s.gaps):
            s.demographics = attempt(s, "no demographics", lambda: census.demographics(s.lat, s.lon))
        if not s.competitors and not any(g.startswith("no competitors") for g in s.gaps):
            s.competitors = attempt(s, "no competitors",
                                    lambda: osm.competitors(s.lat, s.lon, self.brief.businessType,
                                                            self.profile["radiusMi"])) or []
        return sim.simulate(s, self.profile, overrides)

    # --- tools (each returns short text for the model) ------------------------------------------------
    def tools(self) -> list:
        run = self

        def find_candidates() -> str:
            """Search CoStar lease listings that match the brief. Returns the shortlist of site ids."""
            def go():
                found = costar.find_candidates(run.brief)
                picked, props = [], set()
                for s in found:  # priced listings, one per property
                    if s.rentMonthly and s.propertyId not in props:
                        picked.append(s)
                        props.add(s.propertyId)
                # a repeat search keeps already-gathered evidence (sims, aerials) for sites it finds again
                run.sites = {s.id: run.sites.get(s.id, s) for s in picked[:SHORTLIST]}
                r = run.profile["radiusMi"]
                lines = [f"{s.id}: {s.address}, ${s.rentMonthly:,.0f}/mo, {s.sizeSqft:,.0f} sq ft, "
                         f"{costar.workers_nearby(s.lat, s.lon, r, run.brief.city):,} workers within {r} mi"
                         for s in run.sites.values()]
                for s in run.sites.values():  # cards and map pins appear now; odds come once a site is simulated
                    run.emit("site", s.model_dump())
                return f"{len(picked)} priced sites match (showing {len(run.sites)}):\n" + "\n".join(lines)
            return run.step("costar", "Searching CoStar lease listings", None, go)

        def relax_constraint(what: str, reason: str) -> str:
            """Loosen one search limit when too few sites match. what: "rent" (+15%) or "size" (range ±25%)."""
            def go():
                b = run.brief
                if what == "rent":
                    b.maxRentMonthly = round(b.maxRentMonthly * RENT_STEP)
                    change = f"max rent raised to ${b.maxRentMonthly:,.0f}/mo"
                elif what == "size":
                    b.sizeSqftMin = b.sizeSqftMin and round(b.sizeSqftMin * (1 - SIZE_STEP))
                    b.sizeSqftMax = b.sizeSqftMax and round(b.sizeSqftMax * (1 + SIZE_STEP))
                    change = f"size range widened to {b.sizeSqftMin}-{b.sizeSqftMax} sq ft"
                else:
                    raise ValueError('what must be "rent" or "size"')
                run.emit("brief", b.model_dump())
                return change + ". Now call find_candidates again."
            return run.step("replan", f"Re-planning: {reason}", None, go)

        def people_nearby(site_id: str) -> str:
            """Census residents, density and how people commute around one site, plus nearby workers."""
            def go():
                s = run.site(site_id)
                s.demographics = census.demographics(s.lat, s.lon)
                d = s.demographics
                workers = costar.workers_nearby(s.lat, s.lon, run.profile["radiusMi"], run.brief.city)
                return (f"{s.address}: {d.densityPerSqMi or 0:,.0f} residents/sq mi, median income "
                        f"${d.medianIncome or 0:,.0f}, {d.driveShare or 0:.0%} drive to work, {workers:,} workers within "
                        f"{run.profile['radiusMi']} mi")
            return run.step("census", f"Counting people near {site_id}", site_id, go)

        def competitors(site_id: str) -> str:
            """Competing and complementary businesses near one site (OpenStreetMap)."""
            def go():
                s = run.site(site_id)
                s.competitors = osm.competitors(s.lat, s.lon, run.brief.businessType, run.profile["radiusMi"])
                comp = [c for c in s.competitors if c.kind == "competitor"]
                near = ", ".join(f"{c.name} {c.distanceMi} mi" for c in comp[:3])
                return f"{s.address}: {len(comp)} competitors within {run.profile['radiusMi']} mi" + (f" (nearest: {near})" if near else "")
            return run.step("osm", f"Finding competitors near {site_id}", site_id, go)

        def simulate(site_id: str, overrides: dict | None = None) -> str:
            """Odds this site is profitable by month 12 (1,000 simulated futures). overrides: what-if changes,
            e.g. {"newCompetitors": false}, {"accessPenalty": false}, {"rentMonthly": 4000}."""
            def go():
                s = run.site(site_id)
                r = run.run_sim(s, overrides)
                if not overrides:  # only the base case goes on the card
                    s.sim = r
                    run.emit("sim", {"siteId": s.id, "result": r.model_dump()})
                    run.emit("site", s.model_dump())
                risks = "; ".join(f.text for f in r.riskFactors) or "none"
                return (f"{s.address}{' (what-if ' + str(overrides) + ')' if overrides else ''}: "
                        f"{r.pProfitableBy12:.0%} chance of profit by month 12, ~{r.expectedCustomers:.0f} customers/day "
                        f"expected vs {r.breakEvenCustomers:.0f} needed, rent {r.rentShare:.0%} of revenue. Risks: {risks}"
                        + (f". DATA GAPS (say so in the report): {'; '.join(s.gaps)}" if s.gaps else ""))
            label = f"What-if on {site_id}: {overrides}" if overrides else f"Simulating 1,000 futures for {site_id}"
            return run.step("sim", label, site_id, go)

        def inspect_aerial(site_id: str) -> str:
            """Expensive: Vexcel aerial photo of the parcel, scored by vision for visibility and road access."""
            def go():
                s = run.site(site_id)
                s.aerial = vexcel.aerial(s.id, s.lat, s.lon)
                v = attempt(s, "no vision", lambda: vision.score_aerial(vexcel.ortho_jpeg(s.aerial.parcelWkt)))
                if v:
                    s.aerial = s.aerial.model_copy(update=v)
                run.emit("site", s.model_dump())
                a = s.aerial
                return (f"{s.address}: visibility {a.visibilityScore}/5 ({a.visibilityReason}); road access "
                        f"{a.roadAccessScore}/5 ({a.roadAccessReason}); image {a.imageUrl}" if v else
                        f"{s.address}: aerial image {a.imageUrl}, vision scoring failed")
            return run.step("vexcel", f"Reading the aerial photo of {site_id}", site_id, go)

        def inspect_interior(site_id: str) -> str:
            """Expensive: Matterport 3D scan of the space: floor area, rooms, seats, written summary."""
            def go():
                s = run.site(site_id)
                if not s.matterportModelId:
                    s.gaps.append("no 3D scan")
                    return f"{s.address}: no 3D scan for this property"
                s.interior = matterport.interior(s.matterportModelId, s.sizeSqft)
                if matterport.is_building_scan(s.interior.floorAreaSqft, s.sizeSqft):
                    s.gaps.append("3D scan is of the whole building")
                run.emit("site", s.model_dump())
                i = s.interior
                return f"{s.address}: {i.floorAreaSqft:,.0f} sq ft scanned, ~{i.estSeats} seats. {i.summary or ''}"
            return run.step("matterport", f"Opening the 3D scan of {site_id}", site_id, go)

        def finish(ranking: list[str], report: str) -> str:
            """Final answer: site ids best first, and a short markdown report citing numbers for each pick."""
            run.ranking = [i for i in ranking if i in run.sites]
            run.report = report
            return "Done. Stop now."

        return [find_candidates, relax_constraint, people_nearby, competitors, simulate,
                inspect_aerial, inspect_interior, finish]


def ranked(run: Run) -> list[Site]:
    """The agent's ranking first, then any other simulated site by odds, then the not-yet-simulated candidates."""
    rest = sorted((s for i, s in run.sites.items() if i not in run.ranking and s.sim),
                  key=lambda s: s.sim.pProfitableBy12, reverse=True)
    unsimulated = [s for i, s in run.sites.items() if i not in run.ranking and not s.sim]
    return [run.sites[i] for i in run.ranking] + rest + unsimulated


def run_agent(query: str, emit: Callable[[str, dict], None], brief: BusinessBrief | None = None) -> Run:
    """Parse, then let the agent work. Over budget or a model failure -> the fixed pipeline finishes the job."""
    brief = brief or parse_brief(query)
    emit("brief", brief.model_dump())
    run = Run(brief, emit)
    if run.ai_profile:
        emit("step", {"id": "s0", "tool": "profile", "siteId": None, "status": "done",
                      "message": f"No preset for {brief.businessType!r}: business numbers are an AI estimate"})
    prompt = SYSTEM.format(thin=THIN, top=TOP, max_calls=MAX_TOOL_CALLS)
    agent = create_deep_agent(model=chat_model(), tools=run.tools(), system_prompt=prompt)
    try:
        for chunk in agent.stream({"messages": [{"role": "user", "content": f"Brief: {brief.model_dump_json()}"}]},
                                  stream_mode="updates", config={"recursion_limit": 4 * MAX_TOOL_CALLS}):
            for update in (chunk or {}).values():
                for m in (update or {}).get("messages", []) if isinstance(update, dict) else []:
                    for tc in getattr(m, "tool_calls", None) or []:
                        if tc["name"] == "write_todos":
                            todos = tc["args"].get("todos") or []
                            if isinstance(todos, str):  # some models send the list as a JSON string
                                todos = json.loads(todos)
                            emit("plan", {"todos": [{"title": t.get("title") or t.get("content", ""),
                                                     "status": t.get("status", "pending")} for t in todos]})
            if run.report:
                break
    except Exception as e:  # over budget, loops, or the model/provider failed
        emit("step", {"id": "fallback", "tool": "pipeline", "siteId": None, "status": "running",
                      "message": f"Switching to auto mode ({type(e).__name__}: {str(e)[:120]})"})
        from app.agent import pipeline
        pipeline.finish(run)
    emit("report", {"markdown": run.report or "The agent stopped before writing a report."})
    return run
