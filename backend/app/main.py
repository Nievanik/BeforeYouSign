import json
from pathlib import Path

from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Response
from pydantic import BaseModel

from app import config
from app.agent.report import generate_report
from app.models import BusinessBrief, RunResult, SimResult, Site
from app.sim import simulate
from app.tools import costar, matterport, vexcel

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

app = FastAPI(title="BeforeYouSign")
api = APIRouter(prefix="/api")


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


@api.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str):
    # shortcut: only the "golden" fixture exists until /analyze stores real runs (Phase 4)
    if run_id != "golden":
        raise HTTPException(404, "unknown run")
    data = json.loads((FIXTURES / "golden_run.json").read_text())
    run = RunResult(**data)
    if not run.report or "placeholder" in run.report:
        run.report = generate_report(run.brief, run.sites)
    return run


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
