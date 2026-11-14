import json
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException

from app import config
from app.models import RunResult

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


app.include_router(api)
