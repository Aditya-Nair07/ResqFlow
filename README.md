# ResQFlow / ResQFlow-Flood

Closed-loop cyber-physical orchestration for disaster resource dispatch.

| Mode | UI | Scope |
|------|-----|--------|
| **ResQFlow** (general) | [`index.html`](index.html) | Generic incidents → resources, geometry ranking, GAPD |
| **ResQFlow-Flood** | [`flood.html`](flood.html) | Urban flood evacuation: groups → vehicles → shelters under dynamic road inundation |

The general demo is preserved as a reference ([`BASELINE.md`](BASELINE.md)). Flood specialization reuses the same closed-loop pattern with flood-specific simulation, routing, verification and twin evidence.

## ResQFlow-Flood (primary specialization)

**Working title:** *ResQFlow-Flood: Closed-Loop Urban Flood Evacuation under Dynamic Road Inundation*

### Runtime loop

1. **Sense** — deterministic flood grid, road depth, groups, shelters, vehicles  
2. **Prioritize** — Flood-GAPD (evacuation band, vulnerability, deadline, people)  
3. **Rank** — Weighted / Ellipse / Polygon / Hybrid over vehicle–route–shelter candidates  
4. **Twin evidence** — NetworkX graph (`CAN_EVACUATE`, `DELIVERS_TO`, `ROUTE_BLOCKED_BY`)  
5. **Verify** — 8 flood-evacuation checks before actuation  
6. **Actuate** — dispatch, move vehicles, load groups, deliver to shelter  
7. **Feedback** — advance flood tick; reroute or explicit failure on mid-route invalidation  

All feedback is **software-only** (deterministic simulator). This is decision support, not a real flood forecast.

### Run flood evacuation

```bash
# Terminal 1 — API (from repo root)
source .venv/bin/activate          # if you haven't already
pip install -r requirements.txt    # first time only
cd backend
python3 -m uvicorn main:app --reload --port 8000

# Terminal 2 — unified React Operations Desk (friend UX on main API)
cd web && npm install && npm run dev
# http://localhost:5173

# Optional — legacy static UI
python3 -m http.server 5500
# http://localhost:5500/flood.html  ·  report.html
```

If you see `uvicorn: command not found`, use `python3 -m uvicorn ...` as above, or activate `.venv` first.

Merge notes: [`docs/UNIFIED-RESQFLOW-MERGE-CHECKLIST.md`](docs/UNIFIED-RESQFLOW-MERGE-CHECKLIST.md) · status [`docs/UNIFIED-IMPLEMENTATION-STATUS.md`](docs/UNIFIED-IMPLEMENTATION-STATUS.md).

### Citizen sensing (no hardware)

Use **Public Safety View** in the React app, or open **http://localhost:5500/report.html**.
`POST /flood/reports/citizen` (alias `/flood/report`) updates the same plant used by dispatch. 

### Flood API

| Endpoint | Purpose |
|----------|---------|
| `GET /health` | includes `"mode": "flood-evacuation"` |
| `GET /flood/scenarios` | list scenario fixtures |
| `POST /flood/reset?scenarioId=` | reset session |
| `GET /flood/snapshot` | current state |
| `POST /flood/simulate/step` | advance ticks + dispatch |
| `POST /flood/reports/citizen` | citizen sensing → plant |
| `POST /flood/reports/operator` | field/operator sensing |
| `GET /flood/incidents` | groups + reports |
| `POST /flood/incidents/{id}/verify` | verify/reject |
| `POST /flood/incidents/{id}/prioritize` | Flood-GAPD queue |
| `POST /flood/plans/compare` | FASTEST / MAX COVERAGE / SAFE AND FAIR |
| `POST /flood/plans/{id}/approve` | atomic commit (stale tick rejected) |
| `POST /flood/field-updates` | high-trust field form |
| `POST /flood/replan` | replan tick |
| `POST /flood/weather` | Open-Meteo or fixture rainfall context |
| `GET /flood/events` · `/flood/events/stream` | polling + SSE |
| `POST /flood/route/plan` | plan pickup + shelter legs with verification |
| `POST /flood/graph/evidence` | twin evidence for group assignment |
| `GET /flood/traces` | in-session + saved traces |

Traces persist under `data/traces/` as `FL-{scenario}-{tick}-{group}.json`.

### Tests & benchmarks

```bash
python3 -m pytest tests/ -q
node experiments/run_flood_benchmarks.js   # → experiments/results/flood_benchmark_results.csv
```

---

## ResQFlow (general demo)

Browser orchestration in [`index.html`](index.html) with optional FastAPI backend for digital twin evidence, agent council, and AI briefing/report.

### Ranking methods

| Method | Idea |
|--------|------|
| **Weighted** | Multi-factor score (urgency, distance, capability, fuel, route safety) |
| **Ellipse** | Reachability ellipse from base + unit |
| **Polygon** | Hazard-aware service polygon |
| **Hybrid** | `0.4·Weighted + 0.3·Ellipse + 0.3·Polygon` |

**GAPD** orders incidents by priority band + geometry fit + people pressure.

**Closed-loop:** ranking proposes; **8 physical checks** decide actuation; transactional repair on failure.

### Backend setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cd backend && python3 -m uvicorn main:app --reload --port 8000
```

Open **http://localhost:5500/index.html** (or **flood.html** for flood mode).

### Digital twin

- General: [`graph.html`](graph.html) — `POST /graph/evidence`  
- Flood: [`flood-graph.html`](flood-graph.html) — `POST /flood/graph/evidence`  

## Architecture (flood)

```
scenarios/*.json
    ↓
backend/simulator/   — flood depth progression, state machine
backend/routing/     — NetworkX road graph, Dijkstra + depth prediction
backend/dispatch/    — Flood-GAPD, scoring, 8-check verify, repair, reroute
backend/flood_graph.py — semantic evidence graph
flood.html + js/flood/app.js — Canvas map (water, roads, groups, shelters, vehicles)
```

## Limitations & ethics

- Simulated hydrology only; thresholds are illustrative  
- No autonomous emergency command; human operators must validate plans  
- No field hardware integration in this repository  
