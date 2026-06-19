# ResQFlow: Closed-Loop Cyber-Physical Orchestration for Disaster Resource Dispatch

**Feature Implementation Plan** — CPS predictive verification + labeling

**Overall Progress:** `100%` *(4 of 4 steps complete)*

**Codebase baseline:** GitHub `main` @ teammate Tailwind UI merge (`index.html` + `graph.html` use Tailwind CDN, Lucide icons, slate/blue theme). Core sim/API logic unchanged in `<script>`.

---

## TLDR

Add **one core CPS feature** to ResQFlow: **predictive physical feasibility** (fuel-at-arrival + ETA vs urgency) inside the existing verify-then-commit path. Apply **light CPS relabeling** on the **Tailwind UI** (panel titles, nav links, Latest allocation copy) with no new subsystems, panels, or backend routes.

---

## Critical Decisions

- **Decision 1: Client-side only** — Extend `verifyCandidate` / `scoreResource` in `index.html`; no new FastAPI endpoints or schema changes.
- **Decision 2: Predictive checks as verification rules** — Fuel-at-arrival and ETA checks join the existing `checks` array (same `canCommit` + repair flow); no separate CPS module.
- **Decision 3: Simple physics model** — Use existing `distance`, `resource.speed`, `fuelCost`, and `incident.urgency`; short inline comment in `verifyCandidate` if formulas are non-obvious.
- **Decision 4: Tailwind hybrid UI** — Teammate PR restyled layout with **Tailwind utility classes** + **Lucide** icons. Latest allocation panels still use embedded `.alloc-*` CSS from JS templates — update **text strings** in both static HTML and JS render functions; do not revert to pre-Tailwind layout.
- **Decision 5: Labeling only** — Rename copy + optional twin-sync line on Summary status; no Sense–Decide–Act panel, human actuation gate, or telemetry API (deferred).
- **Decision 6: Demo-safe defaults** — Predictive thresholds tuned so normal **Start scenario** demo still completes; repair path must remain visible but not block every allocation.

---

## Current hook points (post–Tailwind merge)

| Area | File | Symbols / IDs |
|------|------|----------------|
| Verification | `index.html` | `verifyCandidate`, `scoreResource` → `canCommit`, `checks` |
| Allocation loop | `index.html` | `runAuction`, `applyAgentCouncil`, `commitAssignment` |
| Latest allocation UI | `index.html` | `renderDecision`, `renderVerification`, `buildAllocationExplainer`, `renderGraphEvidence` |
| Council / graph API | `index.html` | `applyAgentCouncil`, `attachGraphEvidence` → set twin sync here |
| Backend status | `index.html` | `setApiStatus`, `#apiStatus` in Summary panel |
| Session restore | `index.html` | `serializeLiveState`, `restoreLiveSession` (must still work after edits) |
| Graph explorer | `graph.html` | `<title>`, header nav “Digital twin”, badge “Twin” |

**Unchanged behaviour to preserve:** pause on load (`resetDemo(false)`), `resqflow_live` session restore, agent council, graph evidence, briefing/report.

---

## Tasks:

- [x] 🟩 **Step 1: Predictive feasibility logic**
  - [x] 🟩 Add helpers near `verifyCandidate`: `estimateTravelTicks(distance, resource.speed)` and `fuelAtArrival(resource, fuelCost, reserve)`
  - [x] 🟩 Pass `dist` / `resource` into `verifyCandidate` (extend `details` from `scoreResource`) for predictive checks
  - [x] 🟩 Add two checks: `fuel sufficient at arrival` and `ETA within urgency window` (after existing six checks)
  - [x] 🟩 Expose `etaTicks`, `fuelAtArrival`, `estimatedEtaLabel` on score object for Latest allocation display (safe for `serializeTrace`)

- [x] 🟩 **Step 2: Wire into allocation & traces**
  - [x] 🟩 Confirm repair loop unchanged: `bids.find(bid => bid.score.canCommit)` respects new failed checks
  - [x] 🟩 Extend `rejectionReason` for predictive failures (fuel at arrival / ETA window)
  - [x] 🟩 Update `renderVerification` title/explainer: **Physical constraint verification** + mention predictive CPS lookahead
  - [x] 🟩 Update `buildAllocationExplainer` / verdict label: **Actuation command issued** (was “Assignment committed”)
  - [x] 🟩 Optional one-line predictive summary in explainer when ETA/fuel-at-arrival values exist

- [x] 🟩 **Step 3: CPS labeling pass (`index.html`)**
  - [x] 🟩 **Static panel headers** (Tailwind + Lucide, ~lines 655–778): Operations map → **Physical plant (simulated)**; nav “Knowledge graph” → **Digital twin**; keep Lucide icons
  - [x] 🟩 **JS template strings** in `renderDecision`, `renderVerification`, `renderGraphEvidence`, council copy: cyber-physical event log / physical state snapshot / twin-grounded evidence where appropriate
  - [x] 🟩 Add `state.lastTwinSync`; set in `attachGraphEvidence` and `applyAgentCouncil` on success; append to `setApiStatus` e.g. `· Twin sync 14:32:05`
  - [x] 🟩 Do **not** add new panels or change Tailwind layout grid — text-only + status line

- [x] 🟩 **Step 4: CPS labeling (`graph.html`) + validation**
  - [x] 🟩 `<title>` and header: **Digital twin explorer**; nav link text aligned with index (“Digital twin” / “Operations demo”)
  - [x] 🟩 Manual validation on `http://localhost:5500`: backend health shows `graph:networkx`, `agents:council`; predictive thresholds verified on seed scenario (each incident has ≥1 safe candidate)

---

## Progress formula

When a **step** is fully done, set its checkbox to `[x]` and mark subtasks 🟩. Recompute:

**Overall Progress = round(100 × completed_steps / 4)%**

| Step | Status |
|------|--------|
| 1 | 🟩 |
| 2 | 🟩 |
| 3 | 🟩 |
| 4 | 🟩 |

*Update the percentage in the header when any step completes.*

---

## Implementation notes (completed)

- **CPS constants:** `CPS_FUEL_RESERVE_AT_ARRIVAL=5`, `CPS_URGENCY_ETA_BASE=16`, `CPS_URGENCY_ETA_SCALE=0.72` — tuned so seed and late-scenario incidents assign when a capable resource is nearby; distant candidates still fail ETA for repair demos.
- **Priority gate:** lower-urgency incidents are blocked only while a higher-priority pending incident still has a safe assignable resource (prevents deadlock when the urgent incident is unservable).
- **Twin sync:** `markTwinSync()` called after successful council and graph evidence API responses; persisted in `resqflow_live` session.
- **No backend changes** — all CPS logic is client-side in `index.html`.

---

## Out of scope (explicit)

- Human-in-the-loop actuation gate (Feature B)
- Telemetry ingest API
- Architecture diagram / PPT / abstract rewrites
- Backend `schemas.py` or new routes
- README refresh (unless requested separately)
- Restoring removed UI (e.g. Quick request) or changing teammate Tailwind styling beyond label text
