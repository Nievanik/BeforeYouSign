import json
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Response

from app import config
from app.models import RunResult
from app.tools import costar, matterport, vexcel

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures"

app = FastAPI(title="BeforeYouSign")
api = APIRouter(prefix="/api")


@api.get("/health")
def health():
    return {"ok": True, "offline": config.OFFLINE}


@api.get("/runs/{run_id}", response_model=RunResult)
def get_run(run_id: str):
    # shortcut: only the "golden" fixture exists until /analyze stores real runs (Phase 4)
    if run_id != "golden":
        raise HTTPException(404, "unknown run")
    return json.loads((FIXTURES / "golden_run.json").read_text())


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
