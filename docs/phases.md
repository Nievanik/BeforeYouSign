# Phases and progress

Tick boxes as you go (`[ ]` → `[x]`). Owners: **A** = backend/data, **B** = frontend/agent, **AB** = both together.
Each phase ends with a **gate**: a concrete check that must pass before moving on. If a phase overruns by more than 30 min, apply the cut order at the bottom.

**Status:** Phase 2 tools done (gate: `python -m scripts.phase2_gate`; demographics need a Census key) · next: Phase 3 · last updated 2026-11-14

| # | Phase | Time | Owner | Status |
|---|---|---|---|---|
| 0 | Setup and design | before build day | AB | ✅ mostly done |
| 1 | Contract and skeleton | 0:00–0:45 | AB | ✅ |
| 2 | Data and tools | 0:45–4:00 | A (B: UI on fixture) | ✅ (B UI pending) |
| 3 | Simulation | 4:00–6:00 | A (B: charts) | ⬜ |
| 4 | Agent | 4:00–7:30 | B | ⬜ |
| 5 | Integration | 7:30–9:30 | AB | ⬜ |
| 6 | Polish, report, offline | 9:30–11:00 | A + B | ⬜ |
| 7 | Demo and submission | 11:00–12:00 | AB | ⬜ |

---

## Phase 0: Setup and design (done the night before)

- [x] Keys in `.env`, `.gitignore` covers `.env`, the CoStar data and the zips
- [x] CoStar and Vexcel kits unzipped in `Hackathon/API_docs/`
- [x] Verified live: Matterport GraphQL (floor area + rooms), Vexcel property + ortho, OpenRouter free model (vision + tool call)
- [x] Python SSL certificates fixed
- [x] Docs: requirements, file structure, API, data schema, external APIs, simulation, business profiles
- [ ] Buy $10 OpenRouter credit (50 → 1,000 requests/day)
- [ ] `git init` + private repo, both teammates have access and a copy of `.env` (shared privately, never committed)
- [ ] Teammate: Python 3.11+, Node 20+, `pip install certifi`
- [ ] Decide who is A and who is B
- [ ] (Later, optional) Yelp or Google Places key for competitor ratings

**Gate:** both laptops can run `python -c "import ssl, urllib.request; urllib.request.urlopen('https://openrouter.ai')"` and have `.env`.

## Phase 1: Contract and skeleton (AB, 0:00–0:45)

- [x] Freeze `Site`, `Competitor`, `SimResult`, `RunResult` from `data-schema.md` → `backend/app/models.py` + `frontend/src/types.ts`
- [x] Write `backend/fixtures/golden_run.json`: one fake `RunResult` with 3 sites, used by B until real data flows
- [x] Backend skeleton: FastAPI `main.py`, `config.py` (reads `.env`), `cache.py` (JSON file cache + `OFFLINE=1`), `/health`
- [x] Frontend skeleton: Vite + React + TS, MapLibre map renders Houston
- [ ] `backend/requirements.txt` (base done; add the rest when Phase 2 needs them): fastapi, uvicorn, pydantic, pandas (or duckdb), numpy, requests, shapely, pillow, certifi, deepagents, langchain-openai, python-dotenv

**Gate:** `/health` returns ok; the frontend shows a map and loads the fixture.

## Phase 2: Data and tools (A, 0:45–4:00)

Every tool: plain function → returns `models.py` types → cached. Test each one on 1 site.

- [ ] **CoStar** (`tools/costar.py`)
  - [x] Load listings once (the listing already has address, coordinates and photos; the property file isn't needed) (only the columns needed)
  - [x] Candidate filter (active, lease, retail, city) + rent normalization + `rentMonthly` all-in estimate
  - [x] Join `MatterportModelId` from `commercial-properties.csv`, photo URL
  - [x] Workers nearby: `company-detail` employees within radius
  - [x] `tests/test_tools.py`: rent normalization (monthly/yearly, rate 0 → null)
- [x] **Census** (needs free `CENSUS_API_KEY`: the ACS API now requires one) (`tools/census.py`): geocoder → tract, population, land area, income
- [x] **OSM** (`tools/osm.py`): competitors by business type within radius (default attractiveness)
- [x] **Vexcel** (`tools/vexcel.py`): parcel (404 → square), ortho JPEG, `/api/sites/{id}/aerial.jpg`. Parking count dropped (unreliable); Census commute data + vision road access replace it
- [x] **Matterport** (`tools/matterport.py`): floor area, rooms, seat estimate, tour URL
- [x] **Vision** (`tools/vision.py`): OpenRouter model scores visibility + road access from the ortho (JSON)

**Meanwhile B:** query box, site cards, map markers, agent log panel, all from the fixture.

**Gate:** a script prints, for the golden query, ≥5 real Houston sites each with rent, people nearby, competitors, Census travel data and floor area (or a named gap).

## Phase 3: Simulation (A, 4:00–6:00)

- [ ] `config.py`: `BUSINESS_PROFILES` from `business-profiles.md` (5 types)
- [ ] `sim/huff.py`: demand grid, Huff share, calibration `r` from the median competitor
- [ ] `sim/montecarlo.py`: 1,000 × 24 P&L, `pProfitableBy12`, bands, break-even customers, payback
- [ ] Risk factors (top 3, plain-English text with site evidence)
- [ ] `simulate(siteId, overrides)` for agent what-ifs (`simulation.md` §7b)
- [ ] `tests/test_sim.py`: same seed → same result · zero people → 0% · calibration ≈ typical · < 1 s

**Meanwhile B:** profit fan chart + odds bar from fixture `SimResult`.

**Gate:** golden query sites get different, believable odds (not all ~0% or ~100%), and tests pass.

## Phase 4: Agent (B, 4:00–7:30)

- [ ] OpenRouter client (`ChatOpenAI` with base_url), model from `OPENROUTER_MODEL`, 429 backoff, response cache
- [ ] Parse the request → `BusinessBrief` (structured output); unknown business type → LLM-proposed profile tagged "AI estimate"
- [ ] deepagents agent with tools: `find_candidates`, `relax_constraint`, `people_nearby`, `competitors`, `inspect_aerial`, `inspect_interior`, `simulate`, `finish`
- [ ] System prompt enforces the 4 behaviors in `requirements.md` F8: re-plan, triage, investigate, explain
- [ ] Guardrails: max 25 tool calls / 120 s → switch to `pipeline.py`
- [ ] `agent/pipeline.py`: the same tools in a fixed order (fallback)
- [ ] `POST /analyze` + SSE events (`api.md`): plan, step, site, sim, report, done

**Gate:** golden query through the API streams a plan, at least one re-plan or investigation step, and a ranked result. The fallback also works with the LLM turned off.

## Phase 5: Integration (AB, 7:30–9:30)

- [ ] Frontend uses the real `/analyze` + SSE (fixture kept as a dev fallback)
- [ ] Cards fill in live as sites finish; map shows sites + competitors
- [ ] Matterport tour embed works for a real model id; aerial image shows detections
- [ ] Run the golden query end to end 3 times; fix the bugs found

**Gate:** acceptance criteria 1–4 in `requirements.md` §8 pass in the browser.

## Phase 6: Polish, report, offline (9:30–11:00)

- [ ] **A:** one-page report (ranking, why #1, risks, assumptions, "compare sites, don't bank on the dollars") + print to PDF
- [ ] **A:** cache the full golden run; test with `OFFLINE=1` and Wi-Fi off
- [ ] **A:** secrets check: `grep` the repo + browser bundle for keys
- [ ] **B:** editable assumptions panel (rerun the simulation on change)
- [ ] **B:** empty/error/gap states ("no 3D scan", "no rent given", "auto mode")
- [ ] **B:** phone-width check; imagery credit "© Vexcel Imaging US, Inc."

**Gate:** acceptance criteria 5–8 pass.

## Phase 7: Demo and submission (AB, 11:00–12:00)

- [ ] 3-minute script: problem → live query → agent re-plans → aerial + 3D + market for the top site → odds and risks → report
- [ ] Record a backup demo video (from the offline cache)
- [ ] README: what it is, target user, how to run, tracks, data credits (the Amazon track asks for basic documentation)
- [ ] Devpost submission. Tracks: **Business & Enterprise** (required), CoStar, Amazon, LangChain deepagents; Rookie if eligible
- [ ] Rehearse twice

**Gate:** submitted before the deadline, with the video uploaded.

---

## Cut order (if behind)

Cut from the top first:
1. Heatmap on the map
2. Report PDF export (keep the on-screen report)
3. Oblique images (ortho only)
4. Census (use a fixed density per submarket)
5. Editable assumptions panel
6. deepagents → custom loop (LLM picks the next tool, plain while loop). Keep the visible plan and re-plan, because agentic depth is 30% of the CoStar score.
7. `pipeline.py` only (last resort)

**Never cut:** real CoStar sites, profit odds, Vexcel aerial + vision, Matterport tour, live step log, offline cache.

## Later (post-hackathon or if time is left)

- [ ] Competitor ratings via Yelp or Google Places (`tools/yelp.py`)
- [ ] Los Angeles
- [ ] Per-cell Census tracts (remove the density shortcut)
- [ ] Peri track: consult a real owner and use their numbers

## Log

| Time | Who | Note |
|---|---|---|
| 11-14 night | | Phase 0: keys verified, docs written, OpenRouter model chosen: `nvidia/nemotron-3.5-super-vl:free` |
