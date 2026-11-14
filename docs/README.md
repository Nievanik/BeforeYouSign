# BeforeYouSign docs

| Doc | Read it when |
|---|---|
| [BeforeYouSign_pitch.md](BeforeYouSign_pitch.md) | You need the why and the pitch |
| [phases.md](phases.md) | **You want to know what to do next**: phases, checklists, owners, cut order |
| [requirements.md](requirements.md) | You need to know **what** we build and when it's done |
| [file-structure.md](file-structure.md) | You're adding a file and need to know where it goes |
| [api.md](api.md) | You're wiring the frontend to the backend (REST + streaming events) |
| [data-schema.md](data-schema.md) | You need the shape of `Site`, `Competitor`, `SimResult`… or which CoStar field feeds what |
| [external-apis.md](external-apis.md) | You're calling CoStar data, Vexcel, Matterport, OSM, Census, Yelp or the LLM (OpenRouter) |
| [simulation.md](simulation.md) | You're touching the Huff model or Monte Carlo |
| [business-profiles.md](business-profiles.md) | You need default numbers (ticket, costs…) per business type, with sources |

## Quick start (target)

```bash
cp .env.example .env          # then fill in keys (ask a teammate)
cd backend && pip install -r requirements.txt && uvicorn app.main:app --reload   # :8000
cd frontend && npm install && npm run dev                                         # :5173
```

Run offline from cache: `OFFLINE=1 uvicorn app.main:app`.
