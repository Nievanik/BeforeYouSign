# Task split: 12-hour build

Remaining work from `phases.md` (Phases 3–7), split across 3 developers.
Dev 1 takes the heavy backend. Devs 2 and 3 take frontend plus lighter backend.

## Dev 1: core backend

| Hours | Task                                                                                                                                                                                                           |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0–0.5 | Freeze the `simulate(siteId, overrides)` signature and the `SimResult` shape, and post them to the team                                                                                                        |
| 0.5–3 | Simulation: `sim/huff.py` (how customers split between nearby shops) and `sim/montecarlo.py` (1,000 runs × 24 months, chance of profit by month 12, ranges, payback)                                           |
| 3–6.5 | Agent: OpenRouter client with retry on "too many requests" (429), parse the request into a `BusinessBrief`, the deepagents agent with its tools, a prompt that makes it re-plan, and the 25-call / 120 s limit |
| 6.5–8 | `POST /analyze`, streaming its events (plan, step, site, sim, report, done)                                                                                                                                    |
| 8–10  | Integration: run the golden query end to end 3 times and fix bugs                                                                                                                                              |

## Dev 2: live frontend + light backend

| Hours  | Task                                                                                                          |
| ------ | ------------------------------------------------------------------------------------------------------------- |
| 0–1    | **Backend:** `BUSINESS_PROFILES` in `config.py` (5 types, from `business-profiles.md`)                        |
| 1–3    | **Frontend:** query box, map markers for sites and competitors, agent log panel (from the saved example run)  |
| 3–4.5  | **Backend:** risk factors, the top 3 in plain English with site evidence. This plugs into Dev 1's `SimResult` |
| 4.5–6  | **Backend:** `tests/test_sim.py` and the `agent/pipeline.py` fallback (the same tools in a fixed order)       |
| 6.5–9  | **Frontend:** switch to the live `/analyze` stream; cards fill in as each site finishes                       |
| 9–10.5 | **Backend:** cache the golden run and test with `OFFLINE=1` and Wi-Fi off                                     |

## Dev 3: frontend design + light backend

| Hours | Task                                                                                                                                                                     |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 0–2.5 | **Frontend:** profit fan chart and odds bar (from the example run's `SimResult`)                                                                                         |
| 2.5–4 | **Frontend:** empty, error and missing-data states ("no 3D scan", "no rent given"), imagery credit "© Vexcel Imaging US, Inc.", check the Matterport tour in the browser |
| 4–6   | **Frontend:** assumptions panel that reruns the simulation on change (needs Dev 1's `simulate`)                                                                          |
| 6–8   | **Backend + frontend:** one-page report (ranking, why #1, risks, assumptions) that prints to PDF                                                                         |
| 8–9   | Visual polish and a check at phone width                                                                                                                                 |
| 9–10  | Secrets check (search the repo and browser bundle for keys), README, data credits                                                                                        |

## Everyone: last 2 hours

| Hours | Task                                                                         |
| ----- | ---------------------------------------------------------------------------- |
| 10–11 | Demo script (3 minutes), then record the backup video from the offline cache |
| 11–12 | Devpost submission and two rehearsals                                        |

## Handoffs

- **Hour 0.5:** Dev 1 posts the `SimResult` shape, which unblocks both of the others.
- **About hour 6.5:** the `/analyze` stream goes live, and Dev 2 switches the frontend to it.
- **If Dev 1 slips:** use the cut order in `phases.md`. The agent is item 6 (deepagents → a simple custom loop). The profit odds and the live step log are never cut.

## Rules

- Commit and push to `dev`, never `main`. Don't touch teammates' branches.
- Pull before you push; never force-push `dev`.
