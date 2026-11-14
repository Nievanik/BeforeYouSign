# External data and APIs

All keys live in `.env` (see `.env.example`). Every call goes through `backend/app/cache.py`.

## CoStar (local files, no API calls)

- Location: `Hackathon/API_docs/costar-kit/data/*.jsonl`. Docs: `Hackathon/API_docs/costar-kit/index.md`, `models/<dataset>.md`, `concepts/`.
- Load once at startup with `pandas.read_json(path, lines=True)` or DuckDB `read_json_auto`. `commercial-property` is 193 MB and `location-occupancy` is 69 MB, so load only the columns you need.
- **Enums are integers.** Decode with `schemas/enums.json`. Useful ones:
  - `ListingStatus`: 1 = Active
  - `RateBasis`: 1 = Monthly, 2 = Yearly
  - `SpaceUse`: 3 = OfficeRetail, 5 = Retail
  - `ServiceType`: 13 = TripleNet, 7 = FullService, 9 = ModifiedGross
- Joins: listing `propertyId` → property `id`; occupancy `tenantLocationId` → company `id`; `commercial-properties.csv` `PropertyId` → `MatterportModelId`.
- Houston = `researchMarketId` 14, LA = 20.
- Emails and phones in the data are fake. Never present them as real contacts.

## Vexcel (aerial imagery)

- Base `https://api.vexcelgroup.com/v2`, header `X-API-KEY: $VEXCEL_API_KEY`.
- Reference implementation: `Hackathon/API_docs/vexcel-kit/vexcel_quickstart.py` (copy its `send()` retry helper).
- **WKT is `POINT(lon lat)`**. Always send `srid=4326`. Layers: `urban,urban-r,wide-area,urban-g`.

| Call | Use |
|---|---|
| `GET property/extract?wkt=POINT(..)&srid=4326&layer=..&latest=true&include=precomputed&unit-system=imperial` | Parcel polygon + attributes. **404** = no parcel → use 80 m square |
| `POST ortho/extract` `{wkt, srid, layer, buffer-meter: 30, crop: "bounding_box", image-format: "jpeg"}` | Top-down image (returns bytes) |
| `GET oriented/collections?…&layer=urban&product-type=oblique` | Which oblique directions exist (404 = none) |
| `POST oriented/extract` `{…, product-type: "oblique-north", rotation: "natural"}` | Angled view for storefront visibility |
| `POST elements/detect` `{wkt, srid, buffer-meter: 30, images:[…], model-input:{elements:[{label:"parking space", model:"sam3", detection-threshold:0.5}], include:["bbox","confidence"]}}` | Count parking spaces / cars |
| `POST embedding/extract` `{wkt, srid, search-text}` | Optional: find similar places by meaning |

- Use `buffer-meter` ≈ 30 for retail: parking lots are often outside the tenant's parcel.
- 429 → exponential backoff (1, 2, 4, 8, 16 s).
- `include=calculated` is slow, so avoid it.
- Credit: "Imagery © Vexcel Imaging US, Inc."

## Matterport (3D interiors)

- GraphQL `POST https://api.matterport.com/api/models/graph`, basic auth `MATTERPORT_API_KEY:MATTERPORT_API_TOKEN`.
- Playground: `MATTERPORT_PLAYGROUND_URL` (token expires ~2026-11-21).
- Verified query:

```graphql
{ model(id: "oNAvrNiXZS7") {
    name address { address }
    floors { label dimensions { areaFloor units } }
    rooms  { label tags dimensions { areaFloor width depth height units } }
} }
```

- Rooms may have an empty label or no `dimensions`, so handle nulls.
- Other model fields worth exploring: `roomClassifications`, `objectAnnotations`, `dimensionEstimates`, `geocoordinates`, `generatedDescription`.
- Embed: Showcase iframe with `MATTERPORT_SDK_KEY` (allowed domain: localhost).

## Yelp Places API (competitors + popularity)

- Formerly "Fusion". **There's no free tier anymore:** you get a **30-day trial with 5,000 calls**, meant for evaluation, then plans start at $229/month. A hackathon demo fits the trial; don't plan on it after. Key: `YELP_API_KEY` (create at the Yelp developer site with a Yelp account).
- `GET https://api.yelp.com/v3/businesses/search?latitude=..&longitude=..&radius=<meters, max 40000>&categories=bubbletea&limit=50&sort_by=distance`, header `Authorization: Bearer $YELP_API_KEY`.
  - Use: `name`, `rating`, `review_count`, `coordinates`, `distance` (m), `categories`, `is_closed`.
- New openings: same call + `&attributes=hot_and_new`.
- Budget: 2 calls per site × 10 sites × a few dozen test runs is well under 5,000. **Cache everything**: the trial key expires.
- Reviews text needs a paid plan, so we don't use it.
- Fallback if Yelp is unavailable: Google Places API (New) Nearby Search with `rating,userRatingCount` (Enterprise field mask: 1,000 free calls/month, needs a billing account), or OSM without popularity (default attractiveness).

## OpenStreetMap Overpass (free, no key; fallback for competitors)

`POST https://overpass-api.de/api/interpreter`

```
[out:json][timeout:25];
( nwr(around:1609,{lat},{lon})["amenity"~"cafe|fast_food|restaurant"];
  nwr(around:1609,{lat},{lon})["cuisine"~"bubble_tea|coffee_shop"];
  nwr(around:1609,{lat},{lon})["amenity"~"school|university|college"]; );
out center tags;
```

Be polite: one query per site, cached, with a descriptive generic User-Agent.

- Overpass reports timeouts as **HTTP 200 with a `remark`** and an empty list, so check `remark` before trusting "no results". Unscoped `name~` regexes time out: scope them to an amenity first.

## US Census

- Tract from lat/lon: `https://geocoding.geo.census.gov/geocoder/geographies/coordinates?x={lon}&y={lat}&benchmark=Public_AR_Current&vintage=Current_Current&format=json`
- ACS: `https://api.census.gov/data/2023/acs/acs5?get=B01003_001E,B19013_001E,B01002_001E&for=tract:{tract}&in=state:{st}+county:{co}`
- The ACS API **now requires a key** (it redirects to `missing_key.html` without one). Free and instant: api.census.gov/data/key_signup.html → `CENSUS_API_KEY`. The geocoder still needs no key.

## LLM via OpenRouter (agent, vision, report)

No LLM credits are provided at the hackathon. We use **OpenRouter free models** (`:free` suffix) through LangChain's OpenAI-compatible client:

```python
from langchain_openai import ChatOpenAI
llm = ChatOpenAI(base_url="https://openrouter.ai/api/v1",
                 api_key=OPENROUTER_API_KEY, model=OPENROUTER_MODEL)   # e.g. "<vendor>/<model>:free"
```

- Key: `OPENROUTER_API_KEY` from openrouter.ai (free account). Model: `OPENROUTER_MODEL`, which you can change without editing code.
- **Limits on free models:** 20 requests/min. 50 requests/day, rising to **1,000/day after a one-time $10 credit purchase**. Failed calls count. **Buy the $10**, because 50/day runs out after a few test runs.
- **Pick a model** at openrouter.ai/models filtered to free + supports tools + image input. Free models change often, so check the morning of the build. If no free model does both, use one model for the agent and a separate vision model (`OPENROUTER_VISION_MODEL`).
- Free models are weaker at long tool-use chains, so **the pipeline stays deterministic Python** (CoStar → tools → simulation). The LLM only does 4 things: parse the request, read aerial images, write step narration, write the report. That's about 3 + 1 per site calls per run.
- Free providers may log or train on prompts, so never send keys or personal data in prompts (CoStar contacts are fake anyway).
- On 429: back off using `Retry-After`. Cache every LLM response keyed by prompt hash so reruns are free.
- Vision input: the ortho JPEG + one oblique JPEG, both base64. Ask for JSON `{visibilityScore, visibilityReason, roadAccessScore, roadAccessReason}`.
