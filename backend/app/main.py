import asyncio
import json
import secrets
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Response, status
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

from app import config
from app.agent.brief import parse_brief
from app.agent.report import generate_report
from app.agent.run import Run, ranked, run_agent
from app.cache import CacheMiss, cached
from app.models import BusinessBrief, RunResult, SimResult, Site
from app.sim import simulate
from app.tools import costar, matterport, vexcel

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

app = FastAPI(title="BeforeYouSign")
api = APIRouter(prefix="/api")

# In-memory storage for active runs and SSE queues
RUNS: dict[str, dict] = {}


class AnalyzeRequest(BaseModel):
    query: str
    brief: BusinessBrief | None = None


MAX_REPLAY_GAP_S = 2.0


def parse_query_to_brief(query: str) -> BusinessBrief:
    """Rough keyword reading of the query: only used when the LLM parser (agent/brief.py) is unavailable."""
    q = query.lower()

    # Business type
    b_type = "boba"
    for candidate in ("coffee", "fast_casual", "salon", "boutique", "boba", "restaurant"):
        if candidate in q or candidate.replace("_", " ") in q or (candidate == "salon" and "hair" in q):
            b_type = candidate if candidate != "restaurant" else "fast_casual"
            break

    # City
    city = "Los Angeles" if "los angeles" in q or "la" in q.split() else "Houston"

    # Rent
    rent = 6000.0
    for raw in query.replace("$", " ").replace(",", "").split():
        token = raw.strip().lower()
        if token.endswith("k") and token[:-1].isdigit():
            rent = float(int(token[:-1]) * 1000)
            break
        if token.isdigit():
            value = int(token)
            if value >= 1000:
                rent = float(value)
                break

    # Must-haves
    must = []
    if "parking" in q:
        must.append("parking")
    if "drive" in q or "transit" in q:
        must.append("transit access")

    return BusinessBrief(
        businessType=b_type,
        city=city,
        maxRentMonthly=rent,
        mustHaves=must,
    )


def work(run_id: str, req: AnalyzeRequest, brief: BusinessBrief):
    """req is what the user sent (the replay key); brief is the parsed one the agent works from."""
    rec = RUNS[run_id]
    key = {"query": req.query.strip().lower(), "brief": req.brief and req.brief.model_dump()}
    if config.OFFLINE:  # demo without Wi-Fi: replay a recorded live run, agent plan and all
        try:
            replay(run_id, rec, cached("runs", key, lambda: None))
            return
        except CacheMiss:
            pass  # never recorded: the agent fails over to the pipeline, which runs from cached tool data
    started, timed = time.monotonic(), []

    def emit(e, d):
        rec["events"].append((e, d))  # list.append is thread-safe; the SSE reader only reads
        timed.append((round(time.monotonic() - started, 2), e, d))

    try:
        run = run_agent(req.query, emit, brief)
        rec["result"] = RunResult(
            runId=run_id,
            brief=run.brief,
            sites=ranked(run),
            report=run.report,
            createdAt=datetime.now(timezone.utc).isoformat(),
        )
        # only a clean agent run is worth replaying: no fatal error, no switch to auto mode
        if not config.OFFLINE and not any(e == "error" or d.get("id") == "fallback" for _, e, d in timed):
            # shortcut: the first clean run of a query is kept; delete backend/cache/runs/ to re-record
            cached("runs", key, lambda: {"events": timed, "result": rec["result"].model_dump()})
    except Exception as e:
        emit("error", {"message": f"{type(e).__name__}: {e}"[:200], "fatal": True})
    emit("done", {"runId": run_id})


def replay(run_id: str, rec: dict, recording: dict):
    prev = 0.0
    for t, e, d in recording["events"]:
        time.sleep(min(t - prev, MAX_REPLAY_GAP_S))
        prev = t
        rec["events"].append((e, d))
    rec["result"] = RunResult(**{**recording["result"], "runId": run_id})
    rec["events"].append(("done", {"runId": run_id}))


def _get_profile(business_type: str) -> dict:
    profiles = getattr(config, "BUSINESS_PROFILES", {})
    if business_type in profiles:
        return profiles[business_type]
    from app.agent.brief import profile_for
    p, _ = profile_for(business_type)
    return p


class SimulateRequest(BaseModel):
    site: Site
    businessType: str = "boba"
    overrides: dict[str, Any] = {}
    seed: int = 7


@api.post("/simulate", response_model=SimResult)
def simulate_site(req: SimulateRequest):
    try:
        profile = _get_profile(req.businessType)
        return simulate(req.site, profile, req.overrides, seed=req.seed)
    except Exception as e:
        raise HTTPException(400, f"simulation failed: {e}")


class ReportRequest(BaseModel):
    brief: BusinessBrief
    sites: list[Site]


@api.post("/report")
def make_report(req: ReportRequest):
    return {"markdown": generate_report(req.brief, req.sites)}


@api.get("/health")
def health():
    return {"ok": True, "offline": config.OFFLINE}


@api.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
def analyze(req: AnalyzeRequest):
    if not req.query.strip() and not req.brief:
        raise HTTPException(400, "empty query")

    brief = req.brief
    if not brief:
        try:
            brief = parse_brief(req.query)  # LLM: any business type, sizes only when the user gives them; cached
        except Exception:  # OpenRouter down or rate-limited: rough keyword reading so the run still starts
            brief = parse_query_to_brief(req.query)
    run_id = "r_" + secrets.token_hex(3)
    RUNS[run_id] = {"events": [], "result": None}
    threading.Thread(target=work, args=(run_id, req, brief), daemon=True).start()
    return {"runId": run_id, "brief": brief}


@api.get("/runs/{run_id}/events", response_class=EventSourceResponse)
async def run_events(run_id: str):
    rec = RUNS.get(run_id)
    if not rec:
        yield ServerSentEvent(event="error", data={"message": "unknown run", "fatal": True})
        return
    i = 0  # replays from the start, so a reconnect or late subscriber sees every event
    while True:
        while i < len(rec["events"]):
            event, data = rec["events"][i]
            i += 1
            yield ServerSentEvent(event=event, data=data, id=str(i))
            if event == "done":
                return
        await asyncio.sleep(0.2)


@api.post("/runs/{run_id}/sites/{site_id}/simulate", response_model=Site)
def simulate_candidate(run_id: str, site_id: str):
    """Simulate a candidate the agent left out: gathers its Census and competitor data, then runs the 1,000 futures."""
    rec = RUNS.get(run_id)
    if not rec:
        raise HTTPException(404, "unknown run")
    if not rec["result"]:
        raise HTTPException(409, "run not finished")
    site = next((s for s in rec["result"].sites if s.id == site_id), None)
    if not site:
        raise HTTPException(404, "unknown site")
    if not site.sim:  # updates the stored run in place, so a reload keeps it
        site.sim = Run(rec["result"].brief, lambda e, d: None).run_sim(site)
    return site


@api.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str):
    if run_id == "golden":
        run = RunResult(**json.loads((FIXTURES / "golden_run.json").read_text()))
        if not run.report or "placeholder" in run.report:
            run.report = generate_report(run.brief, run.sites)
        return run
    rec = RUNS.get(run_id)
    if not rec:
        raise HTTPException(404, "unknown run")
    if not rec["result"]:
        raise HTTPException(409, "run not finished")
    return rec["result"]


@api.get("/sites/{site_id}/aerial.jpg")
def aerial_jpg(site_id: str):
    # the Vexcel key stays server-side; the browser only sees this proxy
    site = costar.get_site(site_id)
    if not site:
        raise HTTPException(404, "unknown site")
    wkt = vexcel.parcel(site.lat, site.lon)["wkt"]
    return Response(vexcel.ortho_jpeg(wkt, vexcel.detect_parking(wkt)), media_type="image/jpeg")


@api.get("/sites/{site_id}/oblique/{direction}.jpg")
def oblique_jpg(site_id: str, direction: str):
    if f"oblique-{direction}" not in vexcel.DIRECTIONS:
        raise HTTPException(404, "unknown direction")
    site = costar.get_site(site_id)
    if not site:
        raise HTTPException(404, "unknown site")
    wkt = vexcel.parcel(site.lat, site.lon)["wkt"]
    if f"oblique-{direction}" not in vexcel.oblique_directions(wkt):
        raise HTTPException(404, "no angled photo from that direction here")
    return Response(vexcel.oblique_jpeg(wkt, f"oblique-{direction}"), media_type="image/jpeg")


@api.get("/sites/{site_id}/floorplan.jpg")
def floorplan_jpg(site_id: str):
    site = costar.get_site(site_id)
    img = site and site.matterportModelId and matterport.floorplan_jpeg(site.matterportModelId)
    if not img:
        raise HTTPException(404, "no floor plan for this site")
    return Response(img, media_type="image/jpeg")


app.include_router(api)
