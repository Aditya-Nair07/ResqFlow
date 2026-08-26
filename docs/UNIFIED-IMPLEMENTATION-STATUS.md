# Unified ResQFlow-Flood — implementation status

Branch: `feature/unified-resqflow-flood`

## What landed

| Phase | Status | Notes |
|---|---|---|
| 0–8 | Done | Contracts, FastAPI authority, sensing, algorithms, 8-check, events, React desk |
| 9 Chennai fixtures | Done | Seeded into plant on `chennai_2015_review`; data strip + difficulty |
| 10 Tests | Done | 37 pytest passing including Chennai/feedback |

## Chennai + feedback product layer

- Default scenario: **Chennai 2015 Flood**
- Data strip: shelter + report counts/areas from `data/chennai/`
- On reset, historical-style citizen reports inject into the **same plant** (depth + groups)
- Difficulty Normal / Heavy / Crisis adjusts rainfall and shelter capacity on the backend
- Full **Field Update** form (depth, road, people found/boarded, vehicle, shelter full, replan)
- Adaptive Planner compute/approve + reservation ledger always visible
- Public Safety: bilingual, large text, richer rescue form

## Still limited (by design / later)

- Full GeoJSON→NetworkX import of `chennai_roads.geojson` as live graph
- Friend browser `simulation.ts` is not authoritative

## Demo

1. API `:8001`, UI `:5174`
2. Hard-refresh the UI
3. Confirm Chennai strip + seeded CITIZEN incidents
4. Difficulty → Heavy Rain → Run
5. Field Update → BLOCKED → events / replan
6. Compute plan → Approve
