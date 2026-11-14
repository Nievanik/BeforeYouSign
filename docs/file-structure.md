# File structure

```
folder/
├── .env                      # secrets, gitignored
├── .env.example              # variable names only, committed
├── .gitignore
├── docs/                     # requirements.md, pitch, and these design docs
│
├── Hackathon/                # event material (read-only)
│   ├── Tracks/               #   main + special track rules (.docx)
│   └── API_docs/             #   zips gitignored
│       ├── costar-kit/       #   CoStar data; data/ is gitignored
│       │   ├── data/*.jsonl  #     8 datasets, ~420 MB
│       │   ├── models/ concepts/  # field docs and real estate background
│       │   └── schemas/enums.json # integer enum → name
│       └── vexcel-kit/       #   Vexcel tutorial PDF + quickstart.py (reference only)
│
├── backend/
│   ├── requirements.txt      # Python dependencies (not the product spec)
│   ├── app/
│   │   ├── main.py           # FastAPI app, routes, SSE
│   │   ├── config.py         # loads .env; business assumptions (see simulation.md)
│   │   ├── models.py         # Pydantic models (see data-schema.md)
│   │   ├── cache.py          # JSON file cache wrapper used by every tool
│   │   ├── agent/
│   │   │   ├── agent.py      # deepagents setup, system prompt, tool registry
│   │   │   ├── pipeline.py   # fixed-order fallback: same tools, no LLM planning
│   │   │   └── report.py     # final one-page recommendation
│   │   ├── tools/            # one file per data source; each returns models.py types
│   │   │   ├── costar.py     # load JSONL once, find candidates, tenants nearby
│   │   │   ├── vexcel.py     # parcel, ortho image
│   │   │   ├── matterport.py # floor area, rooms, seat estimate
│   │   │   ├── yelp.py       # competitors, rating, review count, hot & new
│   │   │   ├── osm.py        # Overpass fallback for competitors
│   │   │   └── census.py     # ACS demographics by tract
│   │   └── sim/
│   │       ├── huff.py       # demand capture share
│   │       └── montecarlo.py # 1,000-run P&L, profit odds, risk drivers
│   ├── tests/
│   │   ├── test_sim.py       # fixed seed → expected odds; zero demand → 0%
│   │   └── test_costar.py    # rent normalization, candidate filter
│   └── cache/                # <source>/<sha1(request)>.json (commit golden-run files for offline demo)
│
└── frontend/
    ├── package.json
    ├── index.html
    └── src/
        ├── main.tsx
        ├── App.tsx           # query box → progress → results
        ├── api.ts            # fetch + EventSource helpers (see api.md)
        ├── types.ts          # mirrors backend models.py
        └── components/
            ├── QueryBox.tsx
            ├── AgentLog.tsx      # streamed steps
            ├── SiteMap.tsx       # MapLibre: sites, competitors, heatmap
            ├── SiteCard.tsx      # odds, rent, access, seats, risks
            ├── ProfitFan.tsx     # Recharts P10/P50/P90 band
            ├── TourEmbed.tsx     # Matterport Showcase iframe
            └── Report.tsx        # printable one-pager
```

## Rules

- **Tools never call each other.** The agent (or the `/analyze` pipeline) orchestrates; tools stay testable alone.
- **Every external call goes through `cache.py`.** `OFFLINE=1` means cache only, never the network.
- **Secrets only in `config.py`.** No other module reads `os.environ`.
- `frontend/src/types.ts` and `backend/app/models.py` must match. Change both in the same commit.
