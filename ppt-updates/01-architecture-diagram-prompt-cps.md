# Architecture Diagram — Revised AI Prompt (CPS + Current Implementation)

Use this prompt with your diagram tool. **Revise the existing diagram — do not redesign from scratch.**

---

## Prompt (copy below)

Revise the existing ResQFlow architecture diagram for **ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch** (do NOT redesign from scratch). Keep the same overall layout, color style, purple INPUT box at top, green OUTPUT at bottom, blue CLIENT border, green FastAPI BACKEND border, cylinder storage shapes, and numbered circles. Only fix logical flow, labels, and arrows as specified below.

**PROJECT (official title):** **ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch** — simulated **physical plant** (browser map) + **digital twin** (NetworkX graph) + multi-agent council + verify-then-actuate control (FastAPI + optional LLM).

---

### KEEP AS-IS (visual identity)

- **INPUT** (purple): incident details, available resources, vehicle status/fuel, user request/strategy (balanced, urgency-first, risk-aware)
- **OUTPUT** (green): selected resource, deployment/actuation plan, route recommendation, explanation/audit report
- **Module boxes:** Module 1 Auction Engine, Module 2 Verify-then-actuate, Module 3 LLM Council (XAI)
- **Cylinders:** NetworkX graph store + Trace log store
- **Legend:** rectangle = processing, cylinder = storage, dashed borders = client vs backend

---

### CPS FRAMING (add as thin banner or subtitle under title)

**"Sense → Decide → Verify → Actuate → Feedback"**

| CPS term | Diagram label |
|----------|----------------|
| Sensors | Simulated plant state (position, fuel, urgency, risk zones) |
| Control system | Auction + council + verification |
| Actuators | Dispatch / actuation command (route + assignment) |
| Feedback | Traces, twin sync, repair loop, pending when unsafe |
| Digital twin | NetworkX graph (not “persistent DB”) |

---

### CLIENT SECTION (blue dashed box) — relabel steps ①–③

**Title:** `Client — browser / physical plant (simulated)`

| Step | Label |
|------|--------|
| ① | **Sensed physical state** — incidents, resources, fuel, routes, risk zones on operations map |
| ② | **Event serialisation** — UI event router → JSON snapshot (`buildSnapshot`) |
| ③ | **Hybrid control path** — **Client-side auction loop** (④⑤ below run in browser). **HTTP POST** snapshot JSON only to `/agents/council`, `/graph/evidence`, `/briefing`, `/report` — **NOT** `/allocate` |

**Small note inside client box:**  
`Optional demo toggle: Closed-loop (verify-then-actuate) vs Open-loop (score-only dispatch)`

Do **not** show POST entering backend before Module 1 bidding.

---

### BACKEND ENTRY & MODULE 1 (Auction — client-side, show inside client OR note)

**Important implementation truth:** Bidding (④⑤) runs **in the browser**, not in FastAPI. Either:

- **Option A (preferred):** Place ④⑤ inside the **client** blue box with subtitle *“control loop (client)”*, arrows to ⑧ for council API; OR  
- **Option B:** Keep ④⑤ in backend box with footnote *“executed client-side; backend receives snapshot for council/graph only”*

| Step | Label |
|------|--------|
| ④ | **Resource bidding** — all available resources vs incident; read graph context from twin for distance/risk/reachability |
| ⑤ | **Bid evaluation** — weighted score **S = Σ w·factor** (urgency, distance, capability, fuel, route risk) → **ranked list** |

Arrow from ⑤: **"ranked list (top-N, N≈3)"** → ⑧

---

### MODULE 3 — LLM Council (⑧⑨⑩) — BEFORE verification

**Caption under Module 3 title:**  
*"Reviews top-N ranked candidates (not a single pre-verified pick)"*

| Step | Label |
|------|--------|
| ⑧ | **Context builder** — GraphRAG k-hop subgraph from NetworkX cylinder (incident + top-N candidates) |
| ⑨ | **AI agent analysis** — Medical, Logistics, Route specialists → **score deltas + rationales** |
| ⑩ | **Decision synthesis** — merge capped deltas, re-rank → **adjusted ranked list** |

Arrows: ⑧ reads NetworkX (read-only); ⑨→⑩; optional metadata write to Trace log.

---

### MODULE 2 — Verify-then-actuate (⑥⑦) — AFTER council

**Caption under Module 2 title:**  
*"Physical constraint verification — closed-loop feedback gate"*

| Step | Label |
|------|--------|
| ⑥ | **Verification engine** — **8 deterministic checks:** availability, fuel margin, capability, route risk, not double-booked, priority gate, **fuel sufficient at arrival (predictive CPS)**, **ETA within urgency window (predictive CPS)** |
| ⑦ | **Candidate selector** — first candidate that **PASSES all checks** (transactional repair) |

**Arrow from ⑩:** `"adjusted ranked list"` → ⑥

**PASS path (green):** ⑥ PASS → ⑦ → ⑪

**FAIL path (red solid arrow):** from ⑥ — label **"FAIL → transactional repair (next in ranked list)"** — loops to ⑦ picking next candidate. **Do NOT** loop back to ④ or into Module 3.

**Closed-loop vs open-loop (small side note, optional):**  
- **Closed-loop (default):** ⑥ blocks actuation when checks fail → pending allocation  
- **Open-loop (demo):** bypass ⑥ gate — score-only dispatch (show as dashed bypass for teaching only)

---

### FINAL STEP & OUTPUT

| Step | Label |
|------|--------|
| ⑪ | **Actuation command / allocation recommendation** — route + vehicle + team + audit trace + twin-grounded evidence |

Write to **Trace log** cylinder. Arrow ⑪ → **OUTPUT**.

---

### PROCESSING ORDER (add visible note on diagram)

**`Processing order: ④⑤ → ⑧⑨⑩ → ⑥⑦ → ⑪`**  
*(Council advises before physical verification — matches code)*

Renumber circles if needed so evaluators read left-to-right in this order.

---

### STORAGE CYLINDERS — subtitle fixes

**NetworkX graph store:**  
*"In-memory digital twin rebuilt per snapshot (nodes: incidents, resources, bases, risk zones; edges: DISTANCE, CAN_REACH, BLOCKED_BY, …)"*

**Trace log store:**  
*"Audit traces (JSON) — trace ID, scores, 8 verification checks, rejected candidates, control mode (closed/open)"*

Do **NOT** label NetworkX as persistent database or Neo4j.

---

### OUTPUT BOX — minor label updates

- "Selected resource" → **"Actuation target (resource/team)"**
- "Deployment plan" → **"Actuation command (dispatch + route)"**
- "Explanation / audit report" → add **"physical constraint verification + twin evidence path"**

---

### DO NOT INCLUDE

- Neo4j, LangGraph, POST `/allocate`
- Live demo UI screenshots on the diagram
- Abstract text on the diagram
- Thank-you / title clutter

**Output:** One clean landscape architecture diagram, same visual identity, **CPS closed-loop** labels, **council-before-verify** flow, **8-check verification**, **client-side auction** truth.

---

## Checklist after diagram is generated

- [ ] Council (⑧⑨⑩) comes **before** verify (⑥⑦)
- [ ] Verification shows **8 checks** including predictive CPS
- [ ] No `/allocate` endpoint arrow
- [ ] Physical plant + digital twin terms present
- [ ] Fail/repair loop does not re-enter council
- [ ] Cylinders labeled in-memory / audit, not DB
