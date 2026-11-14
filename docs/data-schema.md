# Data schema

Our internal models (Pydantic in `backend/app/models.py`, mirrored in `frontend/src/types.ts`), and where each field comes from. Units: money USD, area sq ft, distance miles, rent **per month** unless named otherwise.

## BusinessBrief

| Field | Type | Example | Source |
|---|---|---|---|
| `businessType` | str | `"boba"` | parsed from the query (LLM) |
| `city` | `"Houston"` \| `"Los Angeles"` | `"Houston"` | parsed |
| `maxRentMonthly` | float | `6000` | parsed |
| `sizeSqftMin` / `sizeSqftMax` | float? | `800` / `2000` | parsed, or default per business type |
| `mustHaves` | list[str] | `["parking"]` | parsed |

## Site

One candidate space.

| Field | Type | Source |
|---|---|---|
| `id` | str | `"L{listingId}-S{spaceId}"` |
| `listingId` | int | listing `id` |
| `propertyId` | int | listing `propertyId` (or `forLeaseSummary.spaces[].propertyId`) |
| `address` | str | property `primaryAddress` (streetNumber + streetName + streetType) |
| `lat`, `lon` | float | property `primaryAddress.latitude/longitude` |
| `sizeSqft` | float | space `squareFeetMax` |
| `rentMonthly` | float? | normalized; see below. `null` if no rate given |
| `rentPsfYear` | float? | normalized |
| `serviceType` | str | space `serviceType` → enum name (TripleNet, FullService…) |
| `spaceUse` | str | space `spaceUse` → enum name (Retail, OfficeRetail…) |
| `photoUrl` | str? | property `primaryPhoto.attachmentUri` (swap `/112/` → `/113/` for 1,400 px) |
| `matterportModelId` | str? | `commercial-properties.csv` on `PropertyId` |
| `aerial` | Aerial? | Vexcel |
| `interior` | Interior? | Matterport |
| `competitors` | list[Competitor] | CoStar tenants + OSM |
| `demographics` | Demographics? | Census |
| `sim` | SimResult? | simulation |
| `gaps` | list[str] | e.g. `["no rent given", "no 3D scan"]` |

### Rent normalization

```
rate = space.rateLow or space.rateHigh         # 0 means "not given" → null
yearly_psf = rate * 12 if rateBasis == 1 (Monthly) else rate   # 2 = Yearly
rentMonthly = yearly_psf * sizeSqft / 12
```
Keep `serviceType`: TripleNet rent excludes taxes, insurance and CAM, so add `commonAreaMaintenanceAmountPerYear` + `propertyTaxAmountPerYear` when present and label the result "est. all-in".

### Candidate filter (CoStar)

`listingStatus == 1` (Active) · `listingType` is a lease type, not 19 (Sublease) · `spaceUse in {5 Retail, 3 OfficeRetail}` **or** property is GeneralRetail · property city = brief city · `rentMonthly <= maxRentMonthly` · size in range.

## Aerial (Vexcel)

| Field | Type | Source |
|---|---|---|
| `parcelWkt` | str | `property/extract` feature geometry (or 80 m square on 404) |
| `visibilityScore` | 1–5 | LLM vision on ortho + oblique, plus `visibilityReason` |
| `roadAccessScore` | 1–5 | LLM vision, plus `roadAccessReason` |
| `collection` | str | `metadata.collection` (capture date for credibility) |
| `parkingSeen` | int? | spaces on the parcel from `elements/detect` "parking space" boxes: each box is a **row**, spaces = row length ÷ 2.75 m. `null` when boxes overlap, aren't row-shaped, or sit off the parcel (diagonal lots). **Display only**, never in the odds |
| `imageUrl` | str | `/api/sites/{id}/aerial.jpg` |
| `obliqueDirections` | list[str] | directions with an angled photo in the newest capture (`oriented/collections`) |

## Interior (Matterport)

| Field | Type | Source (GraphQL on `model(id)`) |
|---|---|---|
| `floorAreaSqft` | float | sum of `floors[].dimensions.areaFloor` (units imperial) |
| `rooms` | list[{label, areaSqft, widthFt, depthFt}] | `rooms[]`. Label and dimensions can be empty, so skip those rooms |
| `estSeats` | int | `(front-of-house area) / 15 sq ft per seat`. Front of house = floor area − kitchen/storage/restroom rooms (or 60% of floor area if rooms are unlabeled) |
| `tourUrl` | str | built from model id |
| `summary` | str? | `generatedDescription.summary`, Matterport's auto-written description of the space |

Floor plan image: `/api/sites/{id}/floorplan.jpg`, from `assets.floorplans` (jpg). The URL expires within hours, so the backend caches the bytes.

> Matterport scans are of the **property**, which may not be the exact listed suite. Show "scan of building" when unsure.

## Competitor

| Field | Type | Source |
|---|---|---|
| `name` | str | company `name` or OSM `name` |
| `kind` | `"competitor"` \| `"complement"` \| `"neutral"` | industry / OSM tag mapping in `config.py` |
| `lat`, `lon`, `distanceMi` | float | property address / OSM node |
| `rating` | float? | Yelp `rating` (1–5) |
| `reviewCount` | int? | Yelp `review_count` |
| `isNew` | bool | in Yelp `attributes=hot_and_new` results |
| `attractiveness` | float | `(rating/4)^2 × log(1+reviewCount)`; defaults 4.0★ / 20 reviews if no Yelp match (see simulation.md) |
| `source` | `"yelp"` \| `"osm"` | |

**Primary source: Yelp.** OSM is the fallback when Yelp fails or the trial runs out. De-duplicate OSM against Yelp by name + distance < 50 m.

> CoStar is **not** used for competitors: `industryType` is "Unknown" on 99% of occupancies. CoStar is used for **daytime workers** instead (below).

## Workers (CoStar, for demand)

`company-detail` records with `numEmployees` and `address.latitude/longitude` (~30.8k locations, ~400k employees). Sum the employees within `radiusMi` of each site into grid cells, then weight them by the profile's `workerWeight`.

## Demographics (Census ACS 5-year)

| Field | ACS variable |
|---|---|
| `population` | `B01003_001E` |
| `medianIncome` | `B19013_001E` |
| `medianAge` | `B01002_001E` |
| `tract` | from Census geocoder on lat/lon |
| `densityPerSqMi` | population ÷ tract `AREALAND` (geocoder) |
| `driveShare` | `B08301_002E / B08301_001E` (commute by car) |
| `walkTransitShare` | `(B08301_010E + B08301_019E) / B08301_001E` |
| `noVehicleShare` | `B08201_002E / B08201_001E` (households without a car) |

The commute shares describe how **residents** travel, used as a proxy for how customers arrive. They replace the aerial parking count. Census can't see a specific lot; the vision `roadAccessScore` covers that.

## SimResult

| Field | Type | Meaning |
|---|---|---|
| `pProfitableBy12` | float 0–1 | **headline:** share of runs where month 12 is profitable |
| `medianMonthProfitable` | int? | median first profitable month (null = not within 24) |
| `profitM12` | {p10, p50, p90} | monthly profit at month 12 |
| `monthlyBands` | list[{month, p10, p50, p90}] | monthly profit, for the fan chart |
| `expectedCustomers` | float | `mean_site` customers/day at maturity |
| `breakEvenCustomers` | float | customers/day needed for profit = 0 |
| `rentShare` | float | rent ÷ expected revenue |
| `paybackMonths` | int? | secondary: median month startup cost is recovered (null = 36+) |
| `peopleNearby` | {residents, workers} | inputs to the demand estimate |
| `riskFactors` | list[{factor, impact, text}] | top 3, e.g. `{"factor": "competitors", "impact": 0.31, "text": "2 competitors within 0.4 mi"}` |
| `assumptions` | dict | the exact inputs used (shown in the report) |
| `seed` | int | for reproducibility |

## RunResult

`{ runId, brief: BusinessBrief, sites: list[Site] (ranked by pProfitableBy12), report: str (markdown), createdAt }`
