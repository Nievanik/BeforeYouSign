# BeforeYouSign

**Simulate a business at a location before you sign the lease.**

---

## Pitch

Opening a small business usually means signing a multi-year lease, often a personal guarantee, based on gut feeling, a walk past the storefront, and a landlord's sales pitch. Large chains don't guess: they pay site-selection firms to model demand before they open. Independent owners can't afford that, and they're the ones who lose the most when a location fails.

**BeforeYouSign** gives an independent owner the same analysis a chain gets, in minutes, for free. You describe the business (_"boba shop in Houston, max $6k/month rent, needs parking"_). An AI agent then:

1. finds available spaces that fit,
2. examines each site from **three angles**:
   - **market data:** rent, size and nearby competitors from CoStar,
   - **from above:** visibility and road access from Vexcel aerial imagery,
   - **from inside:** layout and seating from Matterport 3D scans,
3. **simulates the business 1,000 times** for each site.

The answer isn't a vague score. It's a probability: **"Site A: 81% chance of breaking even within 18 months. Site B: 47%, mainly because two competitors are within 0.4 miles and the lot is hard to drive into in a car-dependent area."**

> Most small businesses sign a lease on gut feeling. This one simulates it first.

---

## Target Audience

| Who                                                                                                                    | Their problem                                                                                        | What they get                                                     |
| ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| **Primary: independent small business owners** (cafés, restaurants, salons, retail) opening a first or second location | Can't afford consultants; one bad lease can wipe out their savings                                   | A ranked shortlist with break-even odds and plain-English reasons |
| **Secondary: commercial real estate brokers and landlords**                                                            | Need to match tenants to spaces that will survive, since a failed tenant means vacancy and lost rent | Evidence to pitch the right space to the right tenant             |
| **Tertiary: small business lenders and city economic-development offices**                                             | Judging whether a loan or grant for a new storefront is likely to succeed                            | A quick, explainable risk estimate for each location              |

---

## Must-Have Features (MVP)

### 1. Agent-driven site search and inspection

Input: business type, budget and target area, in plain English. The agent plans and runs a multi-step investigation:

- searches available spaces (CoStar),
- maps competitors and complementary businesses nearby (CoStar tenants + OpenStreetMap),
- pulls demographics (US Census),
- **reads the aerial image** with a vision model: judges storefront visibility and road access.

The UI streams each step live, so the user sees _why_ the agent concludes what it does.

### 2. Demand and survival simulation

- **Demand:** a Huff gravity model estimates the share of nearby customers each site would capture, given its competitors' size and distance.
- **Monte Carlo P&L:** 1,000 simulated 24-month futures with uncertain demand, average ticket, ramp-up speed and the chance of a new competitor, minus rent, wages and cost of goods.
- **Output:** **probability of breaking even**, a profit range (P10 / P50 / P90), and the **main risk factors** that drove failures.

### 3. Map comparison and decision report

- An interactive map with candidate sites, competitors and a demand heatmap.
- Side-by-side site cards with break-even odds, rent, access and a risk summary.
- A one-page, AI-written recommendation the owner can bring to their bank or landlord.

---

## Why Now

- **The data finally exists in one place.** Market data, aerial imagery and 3D interiors for the same address used to sit in separate, expensive silos. CoStar, Vexcel and Matterport now expose them together through APIs.
- **AI agents can do the analyst's job.** Vision models can read an aerial photo (cars, lots, roads), and agent frameworks can plan multi-step research. Neither was practical or affordable a couple of years ago.
- **More people are starting businesses.** US new-business applications have been running near record levels since 2020, and many of these founders are first-timers with no access to site-selection expertise.
- **The cost of being wrong is high.** About 1 in 5 new businesses close within their first year (US BLS). Commercial leases are long and rents in strong areas keep climbing, so a bad location is often what sinks the business.
- **Main Street needs it.** Post-pandemic vacancies leave empty storefronts that need the _right_ tenants. Better matching helps owners, landlords and neighborhoods at the same time.

---

## MVP Stack

| Layer          | Choice                                                                                                              | Why                                                                                               |
| -------------- | ------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| **Frontend**   | React + Vite, **MapLibre GL** (or Leaflet), **Recharts**                                                            | Fast to build; free map tiles; easy fan and bar charts                                            |
| **Backend**    | **Python + FastAPI**, server-sent events for streaming agent steps                                                  | Python suits data and simulation; streaming makes the agent visible                               |
| **Agent**      | **LangChain deepagents** + **Claude** (tool use + vision)                                                           | Multi-step planning and tool calls; vision for aerial imagery; qualifies for the deepagents prize |
| **Simulation** | **NumPy** (Huff model + vectorized Monte Carlo)                                                                     | About 150 lines; runs in under 1 second per site                                                  |
| **Data**       | CoStar toolkit (SDK / MCP / OpenAPI), Vexcel imagery, Matterport, **US Census ACS API**, **OpenStreetMap Overpass** | CoStar layers for the core; free public data fills the gaps                                       |
| **Storage**    | Local **JSON file cache** of every API response                                                                     | No database needed; the demo works even if APIs fail                                              |
| **Hosting**    | Vercel (frontend) + Render / Fly.io (backend), or run locally for the demo                                          | Free tiers; quick deploy                                                                          |

**Scope for an 18–24 hour hackathon:** one city (Houston or LA), one business type (café / boba), 5–10 candidate sites, one golden-path demo query.

---

## Tracks & Prizes

- **Required track:** Best Business & Enterprise Hack
- **CoStar, "Inside and Out: AI for the Built World":** uses all three data layers together, is agentic, and is useful on Monday
- **Amazon Best Practical AI Innovation:** a real problem, multi-step agent, simple UX
- **LangChain Best Use of deepagents**
