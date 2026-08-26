"""Edge closure helpers."""

from __future__ import annotations

from simulator.flood import FloodSimulator
from routing.road_graph import RoadNetwork


def count_closed_edges(road: RoadNetwork, flood: FloodSimulator, max_depth_cm: float = 25) -> int:
    closed = 0
    seen = set()
    for meta in road.edge_meta.values():
        eid = meta.get("id")
        if eid in seen:
            continue
        seen.add(eid)
        if not road.edge_open(meta, flood, "road", max_depth_cm):
            closed += 1
    return closed
