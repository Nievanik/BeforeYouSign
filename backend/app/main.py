import json
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Response

from app import config
from app.models import RunResult
from app.tools import costar, vexcel

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

app = FastAPI(title="BeforeYouSign")
api = APIRouter(prefix="/api")


import asyncio
import json
from pathlib import Path
import queue
import re
import threading
from typing import Optional
import uuid

from fastapi import APIRouter, FastAPI, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app import config
from app.agent.pipeline import run_pipeline
from app.models import BusinessBrief, RunResult
from app.tools import costar, vexcel

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

app = FastAPI(title="BeforeYouSign")
api = APIRouter(prefix="/api")

# In-memory storage for active runs and SSE queues
RUNS: dict[str, RunResult] = {}
RUN_QUEUES: dict[str, queue.Queue] = {}


class AnalyzeRequest(BaseModel):
    query: str
    brief: Optional[BusinessBrief] = None


def parse_query_to_brief(query: str) -> BusinessBrief:
    """Extract business brief from natural language query."""
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
    rent_match = re.search(r'\$?(\d+)(?:k|\s*,\s*000|\s*000)', q)
    if rent_match:
        val = int(rent_match.group(1))
        rent = float(val * 1000 if val < 100 else val)

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
        sizeSqftMin=800,
        sizeSqftMax=2500,
        mustHaves=must,
    )


@api.get("/health")
def health():
    return {"ok": True, "offline": config.OFFLINE}


@api.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
def analyze(req: AnalyzeRequest):
    if not req.query.strip() and not req.brief:
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    brief = req.brief or parse_query_to_brief(req.query)
    run_id = f"r_{uuid.uuid4().hex[:8]}"

    event_q: queue.Queue = queue.Queue()
    RUN_QUEUES[run_id] = event_q

    def worker():
        try:
            def on_event(event_name: str, data: dict):
                event_q.put((event_name, data))

            result = run_pipeline(brief, max_sites=3, on_event=on_event)
            RUNS[run_id] = result
        except Exception as e:
            event_q.put(("error", {"message": str(e), "fatal": True}))
        finally:
            event_q.put(None)  # Sentinel to close SSE stream

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    return {"runId": run_id, "brief": brief}


@api.get("/runs/{run_id}/events")
def run_events(run_id: str):
    if run_id not in RUN_QUEUES:
        raise HTTPException(404, "Run queue not found")

    event_q = RUN_QUEUES[run_id]

    def sse_generator():
        while True:
            try:
                item = event_q.get(timeout=25)
                if item is None:
                    break
                event_name, data = item
                yield f"event: {event_name}\ndata: {json.dumps(data)}\n\n"
            except queue.Empty:
                # Keep-alive heartbeat comment
                yield ": keep-alive\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")


@api.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str):
    if run_id in RUNS:
        return RUNS[run_id]
    if run_id == "golden":
        return json.loads((FIXTURES / "golden_run.json").read_text())
    raise HTTPException(404, "unknown run")


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

app.include_router(api)
