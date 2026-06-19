# ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch

Single-file orchestration UI in `index.html` (brand: **ResQFlow**).

## Phase 2 — Run with backend (optional)

The simulation runs fully in the browser. **Briefing** and **Report** can call a small FastAPI backend for AI-generated text, with automatic local fallback if the backend is offline.

### 1. Backend setup

```bash
cd disaster_response
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit disaster_response/.env — set AICREDITS_API_KEY (see below)
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 2. Open the UI

Open `index.html` in a browser (double-click or drag into Chrome/Firefox).

The **Summary** panel shows backend status:
- **Connected (aicredits)** — LLM key loaded; Briefing/Report use AI
- **Connected (local text only)** — backend up but no API key
- **Offline** — frontend uses built-in local text

### 3. Health check (terminal)

```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","service":"resqflow-api","llm_configured":true/false,"provider":...}`

### AICredits setup (OpenAI-compatible)

Put your key in **`disaster_response/.env`** (create by copying `.env.example`):

```env
LLM_PROVIDER=aicredits
AICREDITS_API_KEY=sk-your-aicredits-key
AICREDITS_BASE_URL=https://api.aicredits.in/v1
AICREDITS_MODEL=gpt-4o-mini
```

Restart the backend after editing `.env`. The API uses the same OpenAI chat-completions format; only the base URL and key change.

## Phase 3 — Knowledge graph

When the backend is running, each allocation fetches **graph evidence** from `POST /graph/evidence`:
- **Evidence path** — base → resource → risk zone → incident (node/edge chain)
- **Ripple check** — competing incidents, fuel pressure, coverage gaps
- **2-hop subgraph** — neighborhood summary around the incident

Traces are saved to `disaster_response/data/traces/` as JSON for audit replay.

Health check includes `"graph": "networkx"` and `"agents": "council"`.

### Phase 4 — Agent council

With **Agent council** enabled (Controls checkbox), each allocation runs three graph-grounded reviewers before commit:

- **Medical** — capability & urgency  
- **Logistics** — fuel & competing coverage  
- **Route** — risk exposure  

`POST /agents/council` returns merged score deltas; the UI re-ranks candidates. Uses your AICredits/OpenAI key when configured; otherwise rule-based council.

### Knowledge Graph Explorer (`graph.html`)

Visual explorer for reviewers — interactive node-link diagram (vis-network).

1. Run backend + `python3 -m http.server 5500` in `disaster_response/`
2. Open **http://localhost:5500/index.html** → **Start scenario**
3. Click **Graph view** or header **Knowledge graph**
4. On `graph.html`: pan/zoom graph, pick incident, trace, hops; see evidence path glow and ripple panel

**Endpoints:** `POST /graph/full`, `GET /graph/traces`, `GET /graph/traces/{id}`

## Run without backend

Open `index.html` only. No server or API key required. Briefing and Report use local rule-based text.

## Quick test

1. Click **Start scenario**.
2. Watch the **Operations map**: bases, risk zones, incidents, routes.
3. Change **Strategy** and use **Preview** under **Strategy compare**.
4. Use **Quick request** + **Add** for a one-line request, or **Add incident**.
5. Read **Latest allocation** for scores, graph evidence path, and ripple notes.
6. Under **Summary**, use **Briefing** and **Report** (backend optional).

Playbook memory and full trace history still run in logic for scoring and reports; the sidebar panels were removed to reduce clutter.
