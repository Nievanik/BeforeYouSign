import asyncio
import json
import secrets
import threading
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Response
from fastapi.sse import EventSourceResponse, ServerSentEvent
from pydantic import BaseModel

from app import config
from app.agent.run import ranked, run_agent
from app.models import BusinessBrief, RunResult
from app.tools import costar, matterport, vexcel

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

app = FastAPI(title="BeforeYouSign")
api = APIRouter(prefix="/api")
# shortcut: runs live in memory and vanish on restart; persist them if the demo needs reloads after a restart
RUNS: dict[str, dict] = {}


@api.get("/health")
def health():
    return {"ok": True, "offline": config.OFFLINE}


class AnalyzeRequest(BaseModel):
    query: str
    brief: BusinessBrief | None = None


def work(run_id: str, req: AnalyzeRequest):
    rec = RUNS[run_id]
    emit = lambda e, d: rec["events"].append((e, d))  # list.append is thread-safe; the SSE reader only reads
    try:
        run = run_agent(req.query, emit, req.brief)
        rec["result"] = RunResult(runId=run_id, brief=run.brief, sites=ranked(run), report=run.report,
                                  createdAt=datetime.now(timezone.utc).isoformat())
    except Exception as e:
        emit("error", {"message": f"{type(e).__name__}: {e}"[:200], "fatal": True})
    emit("done", {"runId": run_id})


@api.post("/analyze", status_code=202)
def analyze(req: AnalyzeRequest):
    if not req.query.strip():
        raise HTTPException(400, "empty query")
    run_id = "r_" + secrets.token_hex(3)
    RUNS[run_id] = {"events": [], "result": None}
    threading.Thread(target=work, args=(run_id, req), daemon=True).start()
    return {"runId": run_id}


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


@api.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str):
    if run_id == "golden":
        return json.loads((FIXTURES / "golden_run.json").read_text())
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
