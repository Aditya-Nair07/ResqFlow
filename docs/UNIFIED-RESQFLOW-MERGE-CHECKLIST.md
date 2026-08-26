# Unified ResQFlow-Flood Merge Checklist

> **Implementation status (branch `feature/unified-resqflow-flood`):** see [`UNIFIED-IMPLEMENTATION-STATUS.md`](./UNIFIED-IMPLEMENTATION-STATUS.md). Core phases 0–10 are implemented; remaining items are polish (screenshots, full GeoJSON live-graph swap, README attribution).

## Decision

The existing `disaster_response/` repository remains the **main project and technical source of truth**.

`ResqFlow-main/` is a **reference implementation and UX donor**. Its useful screens, workflows, wording, and Chennai fixtures will be ported into the main project. Its browser-only dispatch heuristics and thin FastAPI service will not replace the existing ResQFlow-Flood backend.

## Final ownership by layer

| Layer | Source of truth | Action |
|---|---|---|
| Flood simulator and deterministic state | Main project (`backend/simulator/`) | Keep and extend |
| Road graph and predictive routing | Main project (`backend/routing/`) | Keep and extend |
| Flood-GAPD and geometry ranking | Main project (`backend/dispatch/`) | Keep authoritative |
| Eight verification checks and transactional repair | Main project (`backend/dispatch/`) | Keep authoritative |
| FastAPI session and API | Main project (`backend/main.py`, `backend/flood_service.py`) | Extend |
| Evidence graph and traces | Main project (`backend/flood_graph.py`, `data/traces/`) | Keep and extend |
| Operations Desk UX | Friend project (`ResqFlow-main/src/IncidentDesk.tsx`) | Port and connect to main API |
| Public Safety / citizen-report UX | Friend project (`PublicSafetyView.tsx`) + current `report.html` | Consolidate |
| Adaptive Planner presentation | Friend project (`AdaptivePlannerPanel.tsx`) | Port UI; replace algorithms with backend results |
| Chennai fixtures | Friend project (`ResqFlow-main/data/`) | Validate, normalize, and import |
| Browser-only simulation/dispatch | Friend project (`simulation.ts`, planner heuristics) | Use only for visual reference; retire as authority |
| Friend FastAPI stub | `ResqFlow-main/backend/main.py` | Do not merge as backend |

---

## Phase 0 — Preserve both baselines

- [ ] Create a dedicated integration branch, for example `feature/unified-resqflow-flood`.
- [ ] Do not edit or delete `ResqFlow-main/` during initial integration.
- [ ] Record the current main-project test result.
- [ ] Record the friend-project build and test result.
- [ ] Capture screenshots of:
  - [ ] Main `flood.html`
  - [ ] Friend Operations Desk
  - [ ] Friend Public Safety View
  - [ ] Friend Adaptive Planner
- [ ] Write down the current startup commands for both projects.
- [ ] Confirm the friend/team permits reuse and preserve attribution in documentation.

### Phase 0 acceptance criteria

- Both versions can still be started independently.
- The main project’s existing tests still pass.
- No original algorithm or evidence module has been removed.

---

## Phase 1 — Define one canonical data contract

The backend contract must be defined before porting React components.

### 1.1 Canonical evacuation incident/group

- [ ] Merge the useful fields from the friend `Incident` type into the main flood group model:
  - [ ] `id`
  - [ ] creation/update timestamps
  - [ ] latitude/longitude and grid/road node
  - [ ] area and landmark
  - [ ] report source
  - [ ] reporter identity/role where appropriate
  - [ ] reported water depth
  - [ ] people affected
  - [ ] elderly/children/disabled/pregnant counts
  - [ ] mobility requirement
  - [ ] evacuation deadline
  - [ ] description
  - [ ] optional evidence/photo metadata
  - [ ] severity
  - [ ] Flood-GAPD score and band
  - [ ] confidence/trust score
  - [ ] lifecycle status
  - [ ] assigned vehicle/shelter/route
  - [ ] audit events
- [ ] Keep evacuation as the primary scope; do not reintroduce food delivery, firefighting, or medical diagnosis workflows.
- [ ] Decide how public latitude/longitude is snapped to the deterministic road graph.
- [ ] Eliminate `% 50` coordinate conversion from friend planner logic.

### 1.2 Canonical source/trust model

- [ ] Define report sources:
  - [ ] `CITIZEN`
  - [ ] `WARD_VOLUNTEER`
  - [ ] `FIELD_TEAM`
  - [ ] `OPERATOR`
  - [ ] `PUBLIC_WEATHER_API`
  - [ ] `SIMULATOR`
- [ ] Define source trust separately from severity.
- [ ] Define freshness/staleness rules.
- [ ] Define duplicate-report rules.
- [ ] Ensure high-trust feedback influences priority but never bypasses the eight safety checks.

### 1.3 Canonical lifecycle

- [ ] Use one lifecycle across frontend, backend, traces, and tests:
  - [ ] `REPORTED`
  - [ ] `VERIFIED`
  - [ ] `PRIORITIZED`
  - [ ] `PLAN_PROPOSED`
  - [ ] `RESOURCE_RESERVED`
  - [ ] `DISPATCHED`
  - [ ] `IN_PROGRESS`
  - [ ] `REPLAN_REQUIRED`
  - [ ] `RESOLVED`
  - [ ] `REJECTED`
  - [ ] `DUPLICATE`
  - [ ] `STRANDED`
  - [ ] `ESCALATED`
- [ ] Implement and test allowed status transitions in the backend.

### Phase 1 acceptance criteria

- One Pydantic contract represents citizen reports, operator updates, simulator groups, assignments, and traces.
- React/browser code consumes backend fields instead of maintaining a second incompatible model.

---

## Phase 2 — Make FastAPI the authoritative controller

- [ ] Keep `backend/main.py` in the main project.
- [ ] Do not merge the friend FastAPI stub.
- [ ] Move all state-changing decisions behind the main API.
- [ ] Add or standardize endpoints:
  - [ ] `GET /flood/scenarios`
  - [ ] `POST /flood/reset`
  - [ ] `GET /flood/snapshot`
  - [ ] `POST /flood/simulate/step`
  - [ ] `POST /flood/reports/citizen`
  - [ ] `POST /flood/reports/operator`
  - [ ] `GET /flood/incidents`
  - [ ] `POST /flood/incidents/{id}/verify`
  - [ ] `POST /flood/incidents/{id}/prioritize`
  - [ ] `POST /flood/plans/compare`
  - [ ] `POST /flood/plans/{id}/approve`
  - [ ] `POST /flood/field-updates`
  - [ ] `POST /flood/replan`
  - [ ] `POST /flood/route/plan`
  - [ ] `POST /flood/graph/evidence`
  - [ ] `GET /flood/traces`
- [ ] Add optimistic version/tick checks so stale plans cannot be approved.
- [ ] Ensure vehicle and shelter reservations are atomic.
- [ ] Persist audit and trace records.

### Phase 2 acceptance criteria

- Refreshing the frontend does not erase authoritative incident/mission state.
- No UI component directly changes vehicle or shelter capacity without an API call.
- Every approved dispatch was verified by the backend at the current flood tick.

---

## Phase 3 — Connect sensing to the actual flood plant

This is the most important missing connection in both versions.

### 3.1 Citizen sensing

- [ ] Port the useful Public Safety View reporting workflow.
- [ ] Consolidate it with the current `report.html` behavior.
- [ ] A citizen waterlogging report must:
  - [ ] create/update a report record
  - [ ] update observed depth evidence
  - [ ] affect nearby flood cells or road-edge observations
  - [ ] create/update an evacuation group when people need help
  - [ ] appear immediately in the Operations Desk
  - [ ] create an audit event
- [ ] Keep citizen reports unverified until operator/field corroboration.
- [ ] Add duplicate/stale detection.

### 3.2 Operator and field feedback

- [ ] Port the friend Field Update form.
- [ ] Support one-tap high-trust updates:
  - [ ] road blocked
  - [ ] observed water depth
  - [ ] people found
  - [ ] people boarded
  - [ ] vehicle blocked/broken/delayed
  - [ ] shelter full/closed
  - [ ] reinforcement requested
- [ ] Give operator/field reports higher confidence than citizen reports.
- [ ] Trigger immediate route re-verification on high-trust updates.
- [ ] Set `REPLAN_REQUIRED` when the active plan is invalid.
- [ ] Never continue an unsafe route automatically.

### 3.3 Public weather data

- [ ] Add a provider-neutral sensing interface.
- [ ] Implement Open-Meteo (or another clearly licensed public source) for rainfall context.
- [ ] Cache results and record source/timestamp/freshness.
- [ ] Provide deterministic fixture fallback for offline review demos.
- [ ] Use weather to adjust rainfall/prediction only; do not claim it provides street-level water depth.

### Phase 3 acceptance criteria

- A citizen form visibly changes the same plant used by dispatch.
- An operator road closure immediately invalidates or repairs an active plan.
- Offline deterministic mode still works without internet.

---

## Phase 4 — Preserve and expose the original algorithms

### 4.1 Flood-GAPD

- [ ] Use the main backend `flood_gapd.py` as the only priority authority.
- [ ] Incorporate:
  - [ ] evacuation band
  - [ ] vulnerability
  - [ ] people count
  - [ ] time-to-inundation/deadline
  - [ ] reachability
  - [ ] report trust/freshness as evidence quality
- [ ] Display the GAPD band, score, and reasons in the friend Incident Desk queue.

### 4.2 Candidate ranking

- [ ] Keep all four methods:
  - [ ] Weighted
  - [ ] Ellipse
  - [ ] Polygon
  - [ ] Hybrid
- [ ] Use the flood grid and road graph for route risk.
- [ ] Use Ellipse only as an endurance/reachability heuristic.
- [ ] Use Polygon as flood-cut service-area coverage.
- [ ] Keep route feasibility authoritative.
- [ ] Add Method Compare to the React Operations Desk.
- [ ] Display winning and rejected candidates with score breakdowns.

### 4.3 Adaptive plan names

The friend plan views can remain as presentation strategies, but they must call the same backend candidates:

- [ ] `FASTEST` changes objective weights; it does not bypass checks.
- [ ] `MAXIMUM COVERAGE` changes objective weights; it does not bypass checks.
- [ ] `SAFE AND FAIR` changes objective weights/reserve rules; it does not bypass checks.
- [ ] Each strategy can run with Weighted/Ellipse/Polygon/Hybrid ranking.
- [ ] Document the distinction:
  - Ranking method = how a candidate is scored geometrically/operationally.
  - Plan strategy = how multiple assignments are balanced.

### Phase 4 acceptance criteria

- Friend UI displays values returned by the main algorithms.
- No duplicate browser implementation can disagree with backend Flood-GAPD/ranking.
- The review demo can compare both ranking method and plan strategy without conflating them.

---

## Phase 5 — Enforce the eight-check verification gate

- [ ] Verify every proposed assignment using:
  1. [ ] vehicle available
  2. [ ] capacity and mobility compatible
  3. [ ] safe pickup route exists
  4. [ ] route depth safe now and at predicted arrival
  5. [ ] shelter open and has capacity
  6. [ ] no duplicate assignment and higher-priority groups protected
  7. [ ] sufficient fuel reserve
  8. [ ] arrival before safe-evacuation deadline
- [ ] Return all check results to the Operations Desk.
- [ ] Display `8/8` or explicit failed checks before approval.
- [ ] Re-run all checks at approval/commit time.
- [ ] Re-run relevant checks after every field update.
- [ ] Keep operator override separate:
  - [ ] record reason and actor
  - [ ] never label a failed plan “verified”
  - [ ] unsafe route cannot be forced as a normal dispatch

### Transactional repair

- [ ] Try the next vehicle when a candidate fails.
- [ ] Try the next route.
- [ ] Try the next shelter.
- [ ] Roll back provisional vehicle/shelter reservations on failure.
- [ ] Leave the group pending/stranded only after alternatives are exhausted.
- [ ] Trace every attempted repair and rejection reason.

### Phase 5 acceptance criteria

- Closed-loop mode produces zero commit-time unsafe actuations.
- A failed top candidate produces a visible repair sequence.
- UI approval cannot bypass stale or failed verification.

---

## Phase 6 — Replace heuristic routing with the main road graph

- [ ] Keep the main NetworkX road-routing layer.
- [ ] Import/normalize the friend `chennai_roads.geojson`.
- [ ] Map Chennai lat/lng to road nodes correctly.
- [ ] Remove Manhattan route generation from `simulation.ts` as authority.
- [ ] Compute:
  - [ ] road-edge travel time
  - [ ] observed/current depth
  - [ ] predicted depth at edge arrival
  - [ ] mode-specific traversability
  - [ ] flood-risk penalty
  - [ ] alternate routes
- [ ] Support:
  - [ ] bus shallow-water threshold
  - [ ] truck medium-depth threshold
  - [ ] boat water/boat-access links
- [ ] Recheck active routes each tick/update.
- [ ] Emit `rerouted`, `no_safe_route`, or `vehicle_stranded`.
- [ ] Draw actual selected/alternate routes in the new UI.

### Phase 6 acceptance criteria

- Route lines shown in the UI are returned by the backend.
- A road closure changes the graph and route.
- Pickup and shelter legs are separately verified.

---

## Phase 7 — Port and consolidate the friend UI

Do not copy every file blindly. Port screens in this order.

### 7.1 Operations Desk

- [ ] Port the Incident Response Queue.
- [ ] Port incident detail, severity/confidence reasons, and audit timeline.
- [ ] Replace local recommendation calls with backend plan APIs.
- [ ] Add Flood-GAPD band/score.
- [ ] Add ranking method selector and Method Compare.
- [ ] Add eight-check verification panel.
- [ ] Show route forecast, fuel, vehicle load, shelter reservation, repairs, and reroute reason.

### 7.2 Public Safety View

- [ ] Port bilingual English/Tamil presentation.
- [ ] Port accessibility controls.
- [ ] Port rescue and waterlogging report forms.
- [ ] Use backend report API.
- [ ] Track report status from backend.
- [ ] Keep “not connected to emergency services” disclaimer.

### 7.3 Adaptive Planner

- [ ] Port plan comparison table and reservation ledger.
- [ ] Replace local planner functions with backend results.
- [ ] Port Field Update form.
- [ ] Add operator trust/source display.
- [ ] Add immediate replan event display.

### 7.4 Map and dashboard

- [ ] Show:
  - [ ] water-depth heatmap
  - [ ] road edges
  - [ ] bus/truck closures
  - [ ] boat links
  - [ ] groups/incidents
  - [ ] shelters and capacity
  - [ ] vehicles and phase/load
  - [ ] current and alternate routes
  - [ ] citizen/operator report markers
- [ ] Use one coordinate model.
- [ ] Remove fake hard-coded safe-route lines and fixed ETA text.

### Phase 7 acceptance criteria

- The friend React UI can run without its local `simulation.ts` making dispatch decisions.
- All operational state shown comes from the main FastAPI snapshot/event stream.

---

## Phase 8 — Real-time update mechanism

- [ ] For the review-scale system, use FastAPI SSE or WebSocket rather than RabbitMQ/Kafka.
- [ ] Define events:
  - [ ] report received
  - [ ] report verified/rejected
  - [ ] weather updated
  - [ ] priority changed
  - [ ] plan proposed
  - [ ] plan verified/rejected
  - [ ] dispatch approved
  - [ ] vehicle telemetry update
  - [ ] road closed
  - [ ] shelter status changed
  - [ ] reroute/replan required
  - [ ] evacuation completed/stranded
- [ ] Reconnect automatically after temporary disconnect.
- [ ] Persist events to trace/audit storage.
- [ ] Provide polling fallback.

### Phase 8 acceptance criteria

- Citizen and operator submissions appear without manually refreshing.
- The dashboard recovers after backend/UI reconnection.
- Event loss does not silently advance an unsafe mission.

---

## Phase 9 — Chennai fixture integration

- [ ] Copy normalized fixtures from `ResqFlow-main/data/` into the main project data/scenario structure.
- [ ] Preserve a source/provenance note for every fixture.
- [ ] Validate:
  - [ ] coordinate ranges
  - [ ] duplicate records
  - [ ] timestamps
  - [ ] rainfall units
  - [ ] river-level units
  - [ ] shelter capacity/access fields
  - [ ] road GeoJSON validity
- [ ] Clearly label synthetic/news-derived records as demonstration fixtures.
- [ ] Build one deterministic “Chennai 2015 Review Scenario”.
- [ ] Keep smaller synthetic scenarios for unit/E2E tests.

### Phase 9 acceptance criteria

- Resetting the Chennai scenario produces an identical replay.
- Documentation distinguishes historical inspiration from verified operational data.

---

## Phase 10 — Tests

### Backend unit tests

- [ ] Flood progression and report-based depth injection.
- [ ] Road closure by observed and predicted depth.
- [ ] Citizen/operator trust and freshness.
- [ ] Duplicate/stale report handling.
- [ ] Flood-GAPD ordering.
- [ ] Weighted/Ellipse/Polygon/Hybrid candidate ranking.
- [ ] All eight verification checks independently.
- [ ] Transactional reservation and rollback.
- [ ] Alternate vehicle/route/shelter repair.
- [ ] Mid-route reroute.

### API tests

- [ ] Citizen report → incident/group + plant update.
- [ ] Operator update → route invalidation.
- [ ] Plan compare → backend algorithm outputs.
- [ ] Approve stale plan → rejected.
- [ ] Approve valid plan → atomic reservation.
- [ ] Evidence graph and trace replay.
- [ ] Weather provider failure → fixture fallback.

### End-to-end scenarios

- [ ] Citizen reports rising water → priority changes.
- [ ] Operator confirms blocked road → bus route rejected.
- [ ] Truck/boat selected after bus failure.
- [ ] Near shelter fills → alternate shelter.
- [ ] Group exceeds one vehicle → split/multiple trip.
- [ ] Two critical groups compete for one vehicle.
- [ ] Pickup succeeds → shelter leg becomes unsafe.
- [ ] Vehicle breakdown / low fuel.
- [ ] No safe route → stranded/escalated.
- [ ] API/event connection drops → safe pause/recovery.

### Frontend tests

- [ ] Public report submission.
- [ ] Operator verification and field update.
- [ ] Plan comparison and approval.
- [ ] Verification check display.
- [ ] Live update/reconnect.
- [ ] Tamil/accessibility controls.

---

## Phase 11 — Benchmarks and evaluation

- [ ] Preserve existing flood benchmark cases.
- [ ] Add Chennai scenario cases.
- [ ] Compare:
  - [ ] ranking methods
  - [ ] plan strategies
  - [ ] closed-loop vs open-loop
  - [ ] citizen-only vs operator-confirmed sensing
- [ ] Track:
  - [ ] people evacuated
  - [ ] vulnerable people evacuated before deadline
  - [ ] unsafe actuations
  - [ ] stranded groups
  - [ ] repairs
  - [ ] reroutes
  - [ ] mean evacuation time
  - [ ] route risk
  - [ ] fuel cost
  - [ ] shelter utilization
  - [ ] report-to-decision latency
- [ ] Do not claim field validity.

---

## Phase 12 — Documentation and review demo

- [ ] Update README with one unified startup flow.
- [ ] Update architecture to show:
  - Public/weather/operator sensing
  - Normalization/provenance
  - Flood-GAPD
  - Geometry ranking
  - NetworkX road/twin graphs
  - Eight-check gate
  - Operator approval
  - Actuation
  - Feedback/replan
- [ ] Credit both team contributions.
- [ ] Explain which data is fixture/live/simulated.
- [ ] State limitations and ethical boundary.
- [ ] Update PPT terminology only after integration stabilizes.

### Review demo script

1. [ ] Open Public Safety View.
2. [ ] Submit citizen waterlogging/rescue report.
3. [ ] Show it arriving in Operations Desk.
4. [ ] Operator verifies it and raises trust.
5. [ ] Show Flood-GAPD priority and candidate comparison.
6. [ ] Show one vehicle failing verification.
7. [ ] Show repair selecting another vehicle/route/shelter.
8. [ ] Approve the 8/8 plan.
9. [ ] Submit a field road-closure update.
10. [ ] Show immediate re-verification and reroute/replan.
11. [ ] Open evidence/twin trace.
12. [ ] Reset and replay deterministically.

---

## Things not to do

- [ ] Do not replace the main backend with `ResqFlow-main/backend/main.py`.
- [ ] Do not keep two independent incident/vehicle/shelter states.
- [ ] Do not let the browser approve or mutate resources without backend verification.
- [ ] Do not duplicate Flood-GAPD or geometry ranking in TypeScript.
- [ ] Do not show fake static routes/ETAs as computed output.
- [ ] Do not add Google Maps, photo-depth AI, Kafka, or hardware before the unified loop works.
- [ ] Do not mix food/medical/fire workflows back into the locked evacuation scope.
- [ ] Do not claim live Chennai municipal integration.

---

## Recommended implementation order

1. [ ] Phase 0 — preserve baselines.
2. [ ] Phase 1 — canonical contracts/lifecycle.
3. [ ] Phase 2 — authoritative API.
4. [ ] Phase 3 — sensing drives plant.
5. [ ] Phase 4–6 — expose algorithms, checks, routing.
6. [ ] Phase 7 — port UI screens onto API.
7. [ ] Phase 8 — live events.
8. [ ] Phase 9 — Chennai fixtures.
9. [ ] Phase 10–11 — tests and benchmarks.
10. [ ] Phase 12 — documentation and review demo.

## Unified definition of done

- [ ] Citizen/operator/weather inputs update one authoritative flood state.
- [ ] The same backend runs Flood-GAPD, ranking, routing, verification, repair, and reservation.
- [ ] The React UI displays backend decisions and does not contain a competing dispatcher.
- [ ] Every committed dispatch passes all eight checks at the current tick.
- [ ] Mid-route feedback triggers reroute, replan, or an explicit safe failure.
- [ ] All decisions include evidence, rejected alternatives, repairs, actor, timestamp, and flood tick.
- [ ] Fixed scenarios replay identically.
- [ ] Automated tests cover operational failure cases.
- [ ] The final UI and documentation remain strictly urban flood evacuation decision support.
