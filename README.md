# BeforeYouSign 📍

> **Simulate your small business before you sign the lease.**

BeforeYouSign is a full-stack decision-support tool for small business owners evaluating commercial lease locations. It runs 1,000-iteration Monte Carlo P&L simulations for each candidate site, integrates aerial imagery and 3-D walkthrough data, and produces a one-page executive report you can share with investors or advisors.

Built at **HackPrinceton 2026**.

---

## ✨ Features

| Capability | Detail |
|---|---|
| **Monte Carlo Simulation** | 1,000 runs × 24-month P&L using Huff gravity demand model, CoStar lease data, and Census foot-traffic |
| **Interactive Profit Fan** | P10/P50/P90 bands, break-even line, Month 12 marker, hover scrubbing |
| **Visual Odds Bar** | Color-coded profitability gauge with payback month, rent-%, and top risk badge |
| **What-If Assumption Panel** | Sliders for rent, ticket size, labor, COGS, startup cost; switches for competition & access penalties; instant re-simulation |
| **Vexcel Aerial + Matterport 3-D** | Embedded imagery with parking & road-access scores |
| **Decision Report (PDF)** | One-page printable executive summary: ranking table, why #1 wins, negotiation points, methodology footer |

---

## 🚀 Quick Start

### 1. Environment

```bash
cp .env.example .env
# Fill in your API keys — see .env.example for the required variables
```

### 2. Backend

```bash
# From project root
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

cd backend
uvicorn app.main:app --port 8000 --reload
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev        # → http://localhost:5173
```

The frontend proxies `/api/*` to `http://localhost:8000` via Vite config.

---

## 🧪 Demo mode (no API calls)

For developing without calling the APIs again and again. Two saved datasets: **restaurant** and **hair salon**
(8 CoStar candidates each, all simulated, with Census, competitors, aerial photos, 3D-scan floor plans and the agent's report).

```bash
cd backend && .venv/bin/python -m scripts.record_demo   # once, online: records backend/demo_data/ (local, not in git)
DEMO=1 .venv/bin/uvicorn app.main:app --reload          # Analyze replays a dataset; nothing calls an API
```

A query mentioning salon / hair / barber / beauty gets the salon dataset; anything else gets the restaurant one.
What-if levers and "simulate" still work (they run locally on the saved data).

## 🏗️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Leaflet |
| Backend | Python 3.11, FastAPI, Uvicorn, Pydantic |
| Simulation | NumPy, SciPy (Huff gravity + Monte Carlo) |
| AI Agent | OpenRouter (GPT-4o / Claude 3.5 Sonnet) via `deepagents` |
| Maps | Leaflet.js + OpenStreetMap tiles |

---

## 📊 Data Credits

| Source | Usage |
|---|---|
| **CoStar** | Commercial property listings, lease rates, vacancy |
| **Vexcel Imagery** | High-resolution aerial orthophotos, parking analysis |
| **Matterport** | 3-D interior walkthroughs, seat/layout estimation |
| **US Census ACS 5-Year** | Demographic commute patterns, daytime population |
| **OpenStreetMap** | Base map tiles, road network access scoring |

---

## 🗂️ Project Structure

```
BeforeYouSign/
├── backend/
│   ├── app/
│   │   ├── agent/       # AI agent: brief parsing, report generation
│   │   ├── sim/         # Monte Carlo simulation engine
│   │   └── main.py      # FastAPI routes
│   ├── data/            # Fixture data (golden_run.json)
│   └── tests/
└── frontend/
    └── src/
        ├── components/  # SiteCard, ProfitFan, AssumptionsPanel, Report, SiteMap
        └── types.ts     # Shared TypeScript interfaces
```

---

## 🔐 Secrets

All API keys are loaded from `.env` at the project root (never committed). `.env.example` contains only empty placeholders.

---

## 📄 License

MIT
