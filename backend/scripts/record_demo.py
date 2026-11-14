"""Record the demo datasets used by DEMO=1 (one live run each; this is the only part that calls APIs).

    cd backend && .venv/bin/python -m scripts.record_demo            # both datasets
    cd backend && .venv/bin/python -m scripts.record_demo salon      # just one

Saves backend/demo_data/<name>.json (the run's events + result, every candidate simulated) and fills
backend/demo_data/cache/ with every API response and image the UI asks for (Census, OSM, Vexcel, Matterport, LLM).
"""
import json
import sys
import time
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app import cache, config
from app.agent.run import ranked, run_agent
from app.models import RunResult

DATASETS = {
    "restaurant": "Restaurant in Houston, max $8k/month rent, at least 1500 sq ft, needs parking",
    "salon": "Hair salon in Houston, max $5k/month rent, 1000-1500 sq ft, needs parking",
}


def record(name: str, query: str) -> None:
    started, events = time.monotonic(), []

    def emit(e, d):
        events.append((round(time.monotonic() - started, 2), e, d))
        if e == "step" and d.get("status") != "running":
            print(f"  {e}: {d.get('message', '')[:90]}")

    run = run_agent(query, emit)
    for s in run.sites.values():  # simulation data for every candidate, not just the agent's top 3
        if not s.sim:
            s.sim = run.run_sim(s)
            emit("sim", {"siteId": s.id, "result": s.sim.model_dump()})
            emit("site", s.model_dump())
    result = RunResult(runId=name, brief=run.brief, sites=ranked(run), report=run.report,
                       createdAt=datetime.now(timezone.utc).isoformat())

    # the images the cards load (aerial, angled views, floor plan) go into the demo cache too
    from app.main import app
    client = TestClient(app)
    for s in result.sites:
        urls = []
        if s.aerial:
            urls += [f"/api/sites/{s.id}/aerial.jpg"] + [f"/api/sites/{s.id}/oblique/{d}.jpg"
                                                         for d in s.aerial.obliqueDirections]
        if s.matterportModelId:
            urls.append(f"/api/sites/{s.id}/floorplan.jpg")
        for u in urls:
            print(f"  image {u}: {client.get(u).status_code}")

    path = config.DEMO_DIR / f"{name}.json"
    path.write_text(json.dumps({"query": query, "events": events, "result": result.model_dump()}))
    print(f"saved {path} ({len(result.sites)} sites, {sum(1 for s in result.sites if s.sim)} simulated)")


if __name__ == "__main__":
    if config.DEMO or config.OFFLINE:
        sys.exit("record with DEMO and OFFLINE unset: recording calls the live APIs")
    cache.CACHE_DIR = config.DEMO_DIR / "cache"  # every response lands in the demo dataset
    config.DEMO_DIR.mkdir(parents=True, exist_ok=True)
    for name in sys.argv[1:] or DATASETS:
        print(f"== {name}: {DATASETS[name]}")
        record(name, DATASETS[name])
