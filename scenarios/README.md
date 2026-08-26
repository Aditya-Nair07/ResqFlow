# Flood evacuation scenarios

Deterministic JSON scenarios for ResQFlow-Flood. Same file always produces the same initial layout and replay (no unseeded randomness).

| ID | Description |
|----|-------------|
| `urban_flood_default` | Moderate rainfall, 4 groups, 2 shelters, bus + truck + boat |
| `urban_flood_stress` | Heavy rainfall, central artery floods early |
| `urban_flood_shelter_full` | Near shelter nearly full — tests alternate shelter selection |
| `urban_flood_boat_only` | Deep flood — bus blocked, boat required |
| `urban_flood_no_route` | Isolated group with no passable road link |

## Schema (core fields)

- **gridSize**, **rainfallPerTick**, **drainRate**, **depthSpread**, **lowPoints** — flood model  
- **roadEdges** — `{ id, from, to, travelTime, closureDepthCm? }`  
- **boatLinks** — water-only edges for rescue boats  
- **shelters** — `{ id, x, y, capacity, node, occupancy?, open? }`  
- **groups** — `{ id, x, y, node, people, vulnerability, mobility, deadlineTick }`  
- **vehicles** — `{ id, mode: road|water, maxDepthCm, capacity, fuel, depotNode }`  

Loaded by `backend/simulator/state.py` and exposed via `GET /flood/scenarios`.
