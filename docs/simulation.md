# Simulation

Decisions (agreed 2026-11-14):

1. Demand is built **from population**: residents + daytime workers, shared among competitors by distance and **popularity (Yelp rating + review count)**, plus the risk of **new competitors opening**.
2. Business numbers come from **preset profiles with published benchmarks**; the user can edit them, and unknown business types get LLM-proposed numbers flagged "AI estimate". See [business-profiles.md](business-profiles.md).
3. Random inputs: customers, average ticket, ramp-up, cost of goods %, new competitor opening.
4. Headline: **chance the business is monthly profitable by month 12.**
5. Honesty: the **ranking between sites** is the reliable output; dollar figures depend on assumptions. Say so in the UI and report, and let the user edit inputs.

Pipeline per site: **people nearby → Huff share → daily customers → 1,000 × 24-month P&L → odds + risks.**

## Contract (frozen 2026-11-14)

```python
from app.sim import simulate
simulate(site: Site, profile: dict, overrides: dict | None = None, seed: int = 7) -> SimResult
```

- `profile`: one `BUSINESS_PROFILES` entry from `config.py` (fields as in [business-profiles.md](business-profiles.md)).
- `overrides`: any profile field, `rentMonthly`, or the switches `newCompetitors` / `accessPenalty` (`False` = off). Unknown keys raise `ValueError`.
- Returns `SimResult` (`models.py` and `frontend/src/types.ts`, unchanged). `assumptions` = every input actually used, so the assumptions panel edits them and sends changes back as `overrides`.
- Agent tool: `simulate(siteId, overrides)` looks up the site and the brief's profile, then calls the function above.
- Until the math lands, build against the `sim` blocks in `fixtures/golden_run.json`.

## 1. People nearby (demand points)

A grid of points every ~200 m within the trade radius (profile: `radiusMi`, e.g. 1 mi for boba). Each point *i* has:

```
people_i = residents_i + workerWeight × workers_i
```

| Term | Source |
|---|---|
| `residents_i` | Census: tract population ÷ tract land area (`AREALAND` from the Census geocoder) × cell area. *shortcut: uses the site's own tract density for every cell; upgrade to per-cell tracts if time allows.* |
| `workers_i` | CoStar `company-detail.numEmployees` at company lat/lon, summed into the nearest cell (~400k employees with coordinates across HOU/LA) |
| `workerWeight` | Profile: how much a worker counts vs a resident (boba 0.5, salon 0.1, lunch restaurant 0.8) |

## 2. Huff share (`sim/huff.py`)

Chance that a person at point *i* picks store *j* among all stores of the category within reach (competitors + our site):

```
P(i→j) = (A_j / d_ij^λ) / Σ_k (A_k / d_ik^λ)
```

- `d` = distance in miles, floor 0.05 mi. `λ` = **2** (standard default; 2+ suits convenience categories like coffee [Huff/ArcGIS refs]). Profile can raise it to 2.5 for very local businesses.
- **Attractiveness `A` (popularity):**

```
A_competitor = (rating / 4.0)^β × log(1 + reviewCount)        # Yelp
A_ourSite    = median(A of competitors) × visibility × access   # a new store starts "average"
```

  - `β` = 2 (a 4.5★ shop pulls ~1.27× a 4.0★ shop; a 3.0★ shop ~0.56×).
  - `log(1 + reviews)` = how established/popular it is (50 reviews ≈ 3.9, 1,000 ≈ 6.9).
  - `visibility` = 0.8–1.2 from the Vexcel vision score (1–5 → 0.8 + 0.1 × (score − 1)).
  - `access` = 0.85 if the area is car-dependent (Census `driveShare` ≥ 0.85) **and** the vision `roadAccessScore` ≤ 2, else 1.0. (Replaces the aerial parking count: one snapshot that missed most empty stalls.)
- Competitors with no Yelp match: rating 4.0, reviewCount 20 (labeled "estimated").

## 3. Calibration: people → customers per day

Turning "people with a P(choice)" into "visits per day" needs a visit rate *r* (visits per person per day for this category). Nobody publishes a reliable *r*, so we **calibrate it from existing stores**, once per city and category:

```
pull_j     = Σ_i people_i × P(i→j)            for every existing competitor j found nearby
r          = profile.typicalDailyCustomers / median_j(pull_j)
mean_site  = r × Σ_i people_i × P(i→site)
```

Meaning: "the median existing competitor serves a typical number of customers for its industry". Sites with more people nearby and fewer/weaker competitors score above typical, and sites with less score below. One line of code, and the scale stays realistic.

## 4. New competitors opening

- Yelp `attributes=hot_and_new` gives competitors that opened recently within the radius. Rate per year = `hotAndNewCount / 0.5` (Yelp treats roughly the last ~6 months as "new"; *shortcut: approximate window, label as estimate*).
- If Yelp returns none, use the profile default (e.g. 0.3 / year).
- Per run: number of new entrants over 24 months ~ Poisson(rate × 2), each at a random month. Each entrant is added to the Huff choice set as a median-attractiveness store at a random distance (0.1 to `radiusMi`), so the demand cut depends on how close it is.
  - *shortcut: approximate the cut as `share_with / share_without`, precomputed for 5 distance buckets.*

## 5. Monte Carlo P&L (`sim/montecarlo.py`)

NumPy arrays shaped `(1000 runs, 24 months)`, fixed `seed`.

| Input | Per-run distribution |
|---|---|
| Customers at maturity | Lognormal, median `mean_site`, σ = 0.35 |
| Average ticket | Normal(profile ticket, profile ticketSd), floor 50% of ticket |
| Ramp-up | months to maturity ~ Uniform(profile rampMin, rampMax); linear ramp starting at 40% |
| Cost of goods % | Uniform(profile cogsMin, cogsMax) |
| New competitor | Section 4 |
| Rent | fixed: `Site.rentMonthly` (all-in estimate) |
| Labor | fixed `laborFixedMonthly` + `laborVariablePct` × revenue (salons are mostly commission) |
| Other fixed | fixed `otherFixedMonthly` (utilities, insurance, software, card fees as % in COGS) |

```
revenue[r,m] = customers[r] × ramp[r,m] × compCut[r,m] × ticket[r] × daysOpen
profit[r,m]  = revenue × (1 − cogs[r] − laborVariablePct) − laborFixed − rent − otherFixed
```

## 6. Outputs

| Output | Definition |
|---|---|
| **`pProfitableBy12`** (headline) | share of runs with `profit[:, 11] ≥ 0` (month 12 is profitable) |
| `medianMonthProfitable` | median first month with profit ≥ 0 (or "not within 24") |
| `monthlyProfit` P10/P50/P90 | at month 12, plus monthly bands for the fan chart |
| `breakEvenCustomers` | customers/day needed for profit = 0 at mature ticket; shown next to `mean_site` (easy to explain: "needs 118/day, expected 140") |
| `paybackMonths` (secondary) | median month when cumulative profit covers `startupCost`, if within 36; else "36+" |
| `riskFactors` | top 3 (section 7) |

## 7. Risk factors

For each random input, compare its average in **losing runs** (month-12 profit < 0) vs all runs, divided by its standard deviation. Take the top 3 by size and write them with site evidence:

- low customers → "only 31,000 people within 1 mi, 4 established competitors (avg 4.4★, 600+ reviews)"
- new competitor → "2 shops opened nearby recently"
- rent → shown as **rent ÷ expected revenue**; flag if above the profile's `rentShareMax` (e.g. 15%)

## 7b. What-if runs (for the agent)

The agent calls `simulate(siteId, overrides)` as a tool. `overrides` can change any profile field or switch a factor off (`{"accessPenalty": false}`, `{"newCompetitors": false}`, `{"rentMonthly": 5200}`). This lets the agent test *why* a site scores low ("without the parking penalty: 58% → 71%, so parking is the main problem") and show it in the step log. Same seed, so the difference comes only from the change.

## 8. Tests (`tests/test_sim.py`)

- Same seed → same `pProfitableBy12`.
- Zero people → 0%.
- Rent 0, no competitors, dense area → close to 100%.
- Calibration: a site identical to the median competitor gets ≈ `typicalDailyCustomers`.
- 1,000 runs in under 1 s.
