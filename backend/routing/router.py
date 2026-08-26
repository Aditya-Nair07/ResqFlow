"""Time-aware pathfinding over flood-affected roads."""

from __future__ import annotations

from typing import Any

import networkx as nx

from routing.road_graph import RoadNetwork, _node_key
from simulator.flood import FloodSimulator


def find_path(
    road: RoadNetwork,
    flood: FloodSimulator,
    start: list[int] | tuple[int, int],
    goal: list[int] | tuple[int, int],
    vehicle_mode: str,
    max_depth_cm: float,
    arrival_tick: int | None = None,
) -> dict[str, Any]:
    """Dijkstra with predicted depth at arrival_tick."""
    sk = road.resolve_node(start)
    gk = road.resolve_node(goal)
    if not sk or not gk:
        return {"ok": False, "reason": "no_safe_route", "nodes": [], "edges": [], "travelTime": 0}
    tg = road.build_traversal_graph(flood, vehicle_mode, max_depth_cm, start_tick=flood.tick)
    if sk not in tg or gk not in tg:
        return {"ok": False, "reason": "no_safe_route", "nodes": [], "edges": [], "travelTime": 0}
    try:
        path = nx.shortest_path(tg, sk, gk, weight="weight")
        travel = nx.shortest_path_length(tg, sk, gk, weight="weight")
    except nx.NetworkXNoPath:
        return {"ok": False, "reason": "no_safe_route", "nodes": [], "edges": [], "travelTime": 0}

    edges = []
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        edges.append({"from": u, "to": v})

    if arrival_tick is not None:
        for edge in edges:
            parts = edge["from"].split(",")
            fx, fy = int(parts[0]), int(parts[1])
            parts2 = edge["to"].split(",")
            tx, ty = int(parts2[0]), int(parts2[1])
            pred = max(
                flood.predict_depth_at_tick(fx, fy, arrival_tick),
                flood.predict_depth_at_tick(tx, ty, arrival_tick),
            )
            if pred > max_depth_cm:
                return {"ok": False, "reason": "predicted_depth_unsafe", "nodes": path, "edges": edges, "travelTime": travel}

    return {
        "ok": True,
        "reason": "ok",
        "nodes": path,
        "edges": edges,
        "travelTime": travel,
        "etaTick": flood.tick + int(travel),
    }


def route_risk(path: dict[str, Any], road: RoadNetwork, flood: FloodSimulator) -> float:
    if not path.get("ok"):
        return 100.0
    risk = 0.0
    for edge in path.get("edges", []):
        parts = edge["from"].split(",")
        fx, fy = int(parts[0]), int(parts[1])
        parts2 = edge["to"].split(",")
        tx, ty = int(parts2[0]), int(parts2[1])
        d = max(flood.depth_at(fx, fy), flood.depth_at(tx, ty))
        risk += min(d, 100) * 0.4
    return min(risk, 100.0)
