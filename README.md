# ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch

Browser orchestration UI in `index.html` (brand: **ResQFlow**), with optional FastAPI backend for digital twin evidence, agent council, and AI briefing/report.

## What’s new (geometry + priority dispatch)

Dispatch ranking is no longer weighted-only. Controls expose a **Ranking method**:

| Method | Idea |
|--------|------|
| **Weighted** | Multi-factor score (urgency, distance, capability, fuel, route safety) — Balanced weights |
| **Ellipse** | Reachability ellipse with foci = nearest base + unit; major axis from fuel × speed |
| **Polygon** | Hazard-aware service polygon (risk zones cut coverage); convex hull fit score |
| **Hybrid** | `0.4·Weighted + 0.3·Ellipse + 0.3·Polygon` |

**GAPD** (Geometry-Aware Priority Dispatch) is always on: incidents are ordered by priority band + geometry fit + people pressure (not urgency alone), with soft-reservation of capable units for critical cases.

**Closed-loop verify-then-actuate** is unchanged: ranking proposes candidates; **8 physical checks** (including fuel-at-arrival and ETA vs urgency) decide actuation; failed top picks use transactional repair.

**Method compare** (Preview) shows Weighted / Ellipse / Polygon / Hybrid side by side without committing.

Map overlays draw ellipses (cyan) or service polygons (amber) when those ranking modes are selected.

## Run with backend (optional)

Simulation runs fully in the browser. Backend adds twin evidence, council, and AI text.

### 1. Backend setup

```bash
# from repo root (this folder)
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env — set AICREDITS_API_KEY if you want LLM text
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Open the UI

```bash
# another terminal, repo root
python3 -m http.server 5500
```

Open **http://localhost:5500/index.html**

Summary status:
- **Connected (aicredits)** — LLM key loaded; Briefing/Report use AI  
- **Connected (local text only)** — backend up but no API key  
- **Offline** — local text fallback; twin evidence unavailable  

### 3. Health check

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","service":"resqflow-api",...,"graph":"networkx","agents":"council"}`

### AICredits setup

In `.env` at repo root:

```env
LLM_PROVIDER=aicredits
AICREDITS_API_KEY=sk-your-aicredits-key
AICREDITS_BASE_URL=https://api.aicredits.in/v1
AICREDITS_MODEL=gpt-4o-mini
```

Restart the backend after editing `.env`.

## Digital twin (`graph.html`)

When the backend is running, each allocation can attach **graph evidence** (`POST /graph/evidence`): evidence path, ripple check, neighborhood subgraph. Traces save under `data/traces/`.

Explorer (Focus view):

1. Backend + `python3 -m http.server 5500`
2. **http://localhost:5500/index.html** → **Start scenario**
3. Header **Digital twin** (or Latest allocation → Digital twin)
4. Pick **Incident** / **Trace**, **Refresh**; pan/zoom with mouse (scroll = zoom, drag = pan)

**Endpoints:** `POST /graph/full`, `POST /graph/evidence`, `GET /graph/traces`, `GET /graph/traces/{id}`, `POST /agents/council`

## Agent council

With **Agent council** enabled, three twin-grounded reviewers (Medical / Logistics / Route) re-rank the top candidates before physical verification. LLM when configured; otherwise heuristic council.

## Run without backend

Open `index.html` only (or static server alone). Ranking, GAPD, overlays, and closed-loop still work. Briefing/Report use local text; twin evidence needs the API.

## Quick test

1. **Reset**, then **Method compare → Preview** — compare picks across Weighted / Ellipse / Polygon / Hybrid.  
2. Set **Ranking method** to Ellipse or Polygon — see map overlays.  
3. Keep **Closed-loop** on → **Start scenario**.  
4. Read **Latest allocation** for method, GAPD band, Physical verify 8/8, and scores.  
5. Open **Digital twin** for evidence path + ripple.  
6. Optional: **Briefing** / **Report** under Summary.

## Controls (decluttered)

**Operations:** Start / Pause / Reset · Ranking method · Agent council · Closed-loop  

Always on (no toggles): GAPD priority, geometry overlays for Ellipse/Polygon/Hybrid, Demo speed, Balanced weighted factors.
