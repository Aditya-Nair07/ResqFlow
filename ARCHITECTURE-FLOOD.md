# ResQFlow-Flood architecture

Urban flood evacuation specialization of ResQFlow closed-loop CPS dispatch.

## Data model

| Entity | Key fields |
|--------|----------------|
| Evacuation group | location, people, vulnerability, mobility, deadlineTick, status |
| Shelter | location, capacity, occupancy, node, open |
| Vehicle | mode (road/water), maxDepthCm, capacity, fuel, phase, route |
| Road edge | endpoints, travelTime, closureDepthCm, water flag |
| Flood frame | tick, depth grid, rainfall progression |

## Two graph layers

1. **Road routing graph** (`backend/routing/road_graph.py`) — NetworkX traversal for Dijkstra pathfinding with depth-aware edge closure  
2. **Semantic evidence graph** (`backend/flood_graph.py`) — assignment explanation: `CAN_EVACUATE`, `DELIVERS_TO`, road blocks  

## Control loop

```
Sense (flood + state) → Flood-GAPD → Rank (W/E/P/H) → Twin evidence
    → 8-check verify → Actuate OR repair → Feedback (tick + reroute)
```

### Eight verification checks

1. Vehicle available  
2. Capacity / mobility compatible  
3. Pickup route exists  
4. Route depth safe now + predicted at arrival  
5. Shelter open with capacity  
6. Priority gate (higher-band groups protected)  
7. Fuel sufficient for both legs  
8. Arrival before group deadline  

## Modules

```
backend/simulator/flood.py      — depth progression
backend/simulator/state.py      — session state machine
backend/routing/router.py       — pathfinding + prediction
backend/dispatch/flood_gapd.py  — priority ordering
backend/dispatch/scoring.py     — ranking methods
backend/dispatch/verify.py      — safety gate
backend/dispatch/assign.py      — closed-loop + repair + traces
backend/dispatch/reroute.py     — mid-route replan
backend/flood_service.py        — API sessions
backend/main.py                 — FastAPI endpoints
```

## UI

- `flood.html` — Canvas map: water heatmap, roads, closures, entities  
- `flood-graph.html` — vis-network evidence explorer  

## Scenarios

Deterministic fixtures in `scenarios/*.json` — see `scenarios/README.md`.

## Baseline

General multi-incident demo preserved in `index.html` — see `BASELINE.md`.
