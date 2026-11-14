# BeforeYouSign: Requirements

**Simulate a business at a location before you sign the lease.**
Source of truth for scope: `BeforeYouSign_pitch.md`. This file says what we build and how we know it works.

## 1. Goal

A small business owner types one plain-English request. The app returns a ranked shortlist of real, available spaces, each with a **probability of being monthly profitable within 12 months**, a profit range, and the main reasons, backed by market data (CoStar), aerial imagery (Vexcel) and an interior 3D scan (Matterport).

**Golden-path demo query:**
> "Boba shop in Houston, max $6k/month rent, needs parking."

## 2. Scope

| In scope (MVP) | Out of scope |
|---|---|
| One city: **Houston** | Los Angeles (data exists; stretch goal) |
| **Any business type** via preset profiles (café/boba, restaurant, salon, retail shop) + user-editable assumptions; unknown types get LLM-proposed assumptions flagged as estimates | Custom models per industry |
| 5–10 candidate sites | Every listing in the city |
| Retail / ground-floor lease listings | Sale listings, office, industrial, residential |
| Local run for the demo | Production hosting, accounts, payments |

## 3. Users

- **Primary:** independent owner opening a café, restaurant, salon or shop. Needs a clear yes/no and why.
- **Secondary:** broker / landlord matching a tenant to a space.
- **Tertiary:** lender or city office judging a storefront loan or grant.

The MVP serves the primary user only.

## 4. Functional requirements

### F1. Parse the request
- Extract: business type, city, max monthly rent, must-haves (e.g. parking), optional size range.
- Show the parsed values back to the user so they can correct them.

### F2. Find candidate spaces (CoStar)
- Source: `Hackathon/API_docs/costar-kit/data/commercial-listing-summary.jsonl`, joined to `commercial-property.jsonl` on `propertyId` → `id`.
- Keep: Houston, active, lease listings (direct lease, shopping center, building park; not sublease or sale), retail property or ground-floor retail space.
- Normalize rent to **$/SF/year** and to **$/month** for the space (`rateBasis`: 1 = monthly, 2 = yearly). Treat a rate of 0 as "not given", never as free.
- Filter by max monthly rent and size; return up to 10 candidates with address, lat/lon, size, rent, `MatterportModelId` (via `commercial-properties.csv`), and photo URL.

### F3. Map competitors and neighbors (Yelp, fallback OSM)
- **Yelp:** same-category businesses within the profile radius, with **rating, review count**, and recent openings (`hot_and_new`). Trial key: 5,000 calls, 30 days, so cache everything.
- **OpenStreetMap:** fallback when Yelp is unavailable (no popularity data, so default attractiveness is used).
- CoStar tenants are **not** used for competitors (industry is unknown on 99% of records).
- Output per site: competitor list with distance, rating, review count and a "new" flag.

### F4. People nearby
- **Residents:** Census ACS tract population + land area → density (plus median income and age for the report).
- **Daytime workers:** CoStar `company-detail` employee counts at their lat/lon.

### F5. Inspect from above (Vexcel)
- `property/extract` at the site's lat/lon (WKT is **lon lat**, always `srid=4326`). 404 = no parcel; fall back to an 80 m square.
- `ortho/extract` image of the parcel; `elements/detect` with labels such as `"car"` and `"parking space"` → **parking count**.
- Vision model (OpenRouter) reads the ortho and oblique images → storefront visibility and road access (scored from 1 to 5 with a one-line reason).
- Retry on 429 with backoff (as in `Hackathon/API_docs/vexcel-kit/vexcel_quickstart.py`).

### F6. Inspect from inside (Matterport)
- GraphQL `https://api.matterport.com/api/models/graph`, basic auth `MATTERPORT_API_KEY:MATTERPORT_API_TOKEN`.
- Pull model name, floor area / rooms and dimensions where available → **estimated seats**.
- Embed the 3D tour in the site card (Showcase SDK, `MATTERPORT_SDK_KEY`, localhost only).

### F7. Simulate the business
Full design: [simulation.md](simulation.md). Default numbers: [business-profiles.md](business-profiles.md).
- **Demand from population:** residents (Census) + daytime workers (CoStar companies), shared among competitors with a **Huff model**. Competitor pull = distance + **Yelp popularity (rating, review count)**. Calibrated so the median existing competitor serves a typical number of customers.
- **New competitors:** opening rate from Yelp "hot and new" nearby.
- **Monte Carlo P&L:** 1,000 runs × 24 months per site. The random inputs are customers, average ticket, ramp-up, cost of goods % and new competitors. Rent, labor and overhead are fixed.
- **Outputs per site:**
  - **chance of being monthly profitable by month 12** (headline)
  - median month it turns profitable
  - month-12 profit P10 / P50 / P90
  - customers/day needed vs expected
  - top 3 risk factors
  - payback month (secondary)
- Under 1 s per site, NumPy only. Fixed random seed.
- UI says plainly: compare sites by the ranking; dollar figures depend on assumptions. All assumptions are editable and shown in the report.

### F8. Agent and live progress
CoStar judges give 30% for "agentic depth: reasons, plans, acts; not a chat wrapper". So the **agent decides the steps**, and the tools stay plain, testable Python functions.

- **Agent:** LangChain deepagents + OpenRouter model. It writes a visible plan (deepagents todo list), then calls tools F2–F7.
- **Required agent behaviors** (each must show up in the step log):
  1. **Re-plan on thin results:** fewer than 5 candidates → relax one constraint (rent +15%, size range, nearby submarkets) and say which one and why.
  2. **Triage:** run cheap checks (rent, competitors, people nearby, quick simulation) on every site; run expensive checks (Vexcel detection + vision, Matterport) only on the top ~5.
  3. **Investigate weak or surprising results:** e.g. low odds → check whether parking or competition drives it (rerun the simulation without that factor) before ranking; a missing scan or parcel → note the gap and continue.
  4. **Explain:** final ranking with evidence links (number, image or source).
- **Fallback:** `pipeline.py` runs the same tools in a fixed order if the model fails or loops (more than 25 tool calls or 120 s). The UI labels a fallback run "auto mode".
- Backend streams every plan update and tool call to the UI (SSE).

### F9. Results UI
- **Map** (MapLibre or Leaflet) with candidate sites, competitors and a demand heatmap.
- **Site cards**, side by side, showing chance profitable by month 12, rent per month, size, parking count, seats, top risks, aerial thumbnail and a "View 3D tour" button.
- **Charts** (Recharts): a fan chart of monthly profit and a "profitable by month 12" bar per site.

### F10. Decision report
- One-page, AI-written recommendation: the ranking, why the top pick wins, the risks and the key assumptions.
- Exportable (print to PDF is enough).

## 5. Non-functional requirements

| Area | Requirement |
|---|---|
| **Secrets** | All keys come from `.env` (gitignored). Never sent to the browser except the Matterport SDK key, which is domain-locked. Never in commits, slides or screenshots. |
| **Resilience** | Every external API response is cached as a local JSON file and the cache is checked first. The demo must run fully offline from that cache if APIs fail. |
| **Speed** | Golden-path query completes in **≤ 90 s** live and **≤ 10 s** from cache. |
| **Honesty** | Show probabilities, not scores. Label estimates and data gaps (missing rent, no parcel, no scan). Don't claim precision the data doesn't support. |
| **Rate limits** | Backoff on 429 for Vexcel; batch where possible. |
| **Data rules** | CoStar contact emails and phones are fake, so never show them as real. Credit imagery as "© Vexcel Imaging US, Inc." |
| **Accessibility** | Readable at phone width; probabilities shown as text, not only color. |

## 6. Architecture

```
React + Vite (MapLibre, Recharts, Matterport embed)
        │  HTTP + SSE
FastAPI (Python)
  ├─ agent/        deepagents + OpenRouter LLM (plan → act → re-plan); pipeline.py = fixed-order fallback
  ├─ tools/        costar.py · vexcel.py · matterport.py · osm.py (yelp.py later) · census.py · simulate
  ├─ sim/          huff.py · montecarlo.py
  └─ cache/        one JSON file per API response
Data: Hackathon/API_docs/costar-kit/data/*.jsonl loaded once at startup (pandas or DuckDB)
```

## 7. Data and keys

| Source | Location / endpoint | Key in `.env` |
|---|---|---|
| CoStar | `Hackathon/API_docs/costar-kit/` (local files; docs in `index.md`, `models/`, `concepts/`) | `COSTAR_ZIP_PASSWORD` (zip only) |
| Vexcel | `https://api.vexcelgroup.com/v2`, header `X-API-KEY` | `VEXCEL_API_KEY` |
| Matterport API | `https://api.matterport.com/api/models/graph`, basic auth | `MATTERPORT_API_KEY`, `MATTERPORT_API_TOKEN` |
| Matterport SDK | Showcase embed, localhost | `MATTERPORT_SDK_KEY` |
| Matterport playground | GraphiQL (token expires ~2026-11-21) | `MATTERPORT_PLAYGROUND_URL` |
| Yelp Places API | `api.yelp.com/v3/businesses/search` (30-day trial, 5,000 calls) | `YELP_API_KEY` (not set yet) |
| OpenStreetMap | Overpass API (free, no key) | none |
| US Census | ACS 5-year API (free) | none for low volume |

Known data facts:
- Houston has ~16 active direct-lease retail listings, plus ground-floor space in apartment buildings. That is enough for 5–10 candidates.
- Enums are integers; decode with `Hackathon/API_docs/costar-kit/schemas/enums.json`.

## 8. Acceptance criteria (demo-ready)

1. Typing the golden-path query returns 5–10 real Houston spaces within the rent limit.
2. Every site card shows: chance profitable by month 12, P10/P50/P90, rent per month, parking count from Vexcel, and a working Matterport tour (or a clear "no scan" note).
3. At least one card explains its lower odds in plain English that names competitors and distances, e.g. "two competitors within 0.4 mi, limited parking".
4. The agent's plan and steps stream live in the UI, and the golden run shows at least one re-plan or investigation step (not just a fixed sequence).
5. The report exports to one page.
6. With the network off, the same query still runs from cache.
7. No secret appears in the repo, the browser bundle or the UI.
8. Simulation code has a small test: fixed seed → same result; zero demand → 0%.

## 9. Build plan: 2 people, 1 day

Phases, owners, checklists and the cut order are tracked in **[phases.md](phases.md)**.

## 10. Prize tracks (requirements that feed them)

- **Required track: Business & Enterprise.**
- **CoStar "Inside and Out"** (30% data use, 30% agentic depth, 25% usefulness, 15% demo): all three layers on the same site (F2 + F5 + F6), agent behaviors in F8, aerial + 3D for spatial and visual understanding.
- **LangChain deepagents:** F8 agent built on deepagents.
- **Amazon Practical AI:** multi-step agent, simple UX, real problem.
- **Peri Forward Deployed:** one real local owner's decision, with name, role and evidence (see Open questions).

## 11. Open questions

1. **Real owner (Peri track):** none yet, so this track is a stretch. If time allows, message one local owner and use their numbers as a case study.
2. ~~Team and deadline~~ **Resolved:** 2 people, 1 day (see §9).
3. ~~Business type~~ **Resolved:** stay open: preset profiles + editable assumptions.
4. ~~Business assumptions~~ **Resolved:** see [simulation.md](simulation.md) and [business-profiles.md](business-profiles.md). Original question: do we have real numbers (ticket, daily customers, margins), or should we use industry benchmarks?
5. ~~Matterport data depth~~ **Resolved:** `floors[].dimensions.areaFloor` and `rooms[].dimensions` (see [external-apis.md](external-apis.md)).
6. **LLM:** no credits provided, so we use OpenRouter free models (buy $10 once for 1,000 req/day). Get `OPENROUTER_API_KEY`; pick a free model with tools + vision (see external-apis.md).
7. **Competitor popularity (deferred):** Yelp needs a business email and Google Places setup failed, so **start with OpenStreetMap** (names + locations; every competitor gets default attractiveness = 4.0★ / 20 reviews). Add ratings later via Yelp or Google Places; only `tools/yelp.py` changes, the simulation already handles both.

Detailed design: see [README.md](README.md).
