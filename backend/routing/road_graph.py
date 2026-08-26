"""Road network for flood evacuation routing."""

from __future__ import annotations

from typing import Any

import networkx as nx

from simulator.flood import FloodSimulator


def _node_key(coord: list[int] | tuple[int, int]) -> str:
    return f"{int(coord[0])},{int(coord[1])}"


class RoadNetwork:
    def __init__(self):
        self.g = nx.MultiGraph()
        self.edge_meta: dict[tuple[str, str, int], dict[str, Any]] = {}

    @classmethod
    def from_scenario(cls, scenario: dict[str, Any]) -> RoadNetwork:
        net = cls()
        for edge in scenario.get("roadEdges", []):
            net.add_road_edge(edge, water=False)
        for edge in scenario.get("boatLinks", []):
            net.add_road_edge(edge, water=True)
        return net

    def add_road_edge(self, edge: dict[str, Any], water: bool = False) -> None:
        a, b = edge["from"], edge["to"]
        ka, kb = _node_key(a), _node_key(b)
        self.g.add_node(ka, x=a[0], y=a[1])
        self.g.add_node(kb, x=b[0], y=b[1])
        key = self.g.add_edge(ka, kb, id=edge.get("id", f"{ka}-{kb}"), water=water)
        self.edge_meta[(ka, kb, key)] = {
            "id": edge.get("id"),
            "travelTime": edge.get("travelTime", 4),
            "closureDepthCm": edge.get("closureDepthCm", 30 if not water else 999),
            "water": water,
            "from": a,
            "to": b,
        }
        key2 = self.g.add_edge(kb, ka, id=edge.get("id", f"{kb}-{ka}"), water=water)
        self.edge_meta[(kb, ka, key2)] = {
            **self.edge_meta[(ka, kb, key)],
            "from": b,
            "to": a,
        }

    def edge_depth_cm(self, meta: dict[str, Any], flood: FloodSimulator) -> float:
        fx, fy = meta["from"]
        tx, ty = meta["to"]
        return max(flood.depth_at(fx, fy), flood.depth_at(tx, ty))

    def edge_open(
        self,
        meta: dict[str, Any],
        flood: FloodSimulator,
        vehicle_mode: str,
        max_depth_cm: float,
        at_tick: int | None = None,
    ) -> bool:
        if meta.get("water") and vehicle_mode != "water":
            return False
        if not meta.get("water") and vehicle_mode == "water":
            depth = self.edge_depth_cm(meta, flood)
            return depth >= 15
        fx, fy = meta["from"]
        tx, ty = meta["to"]
        if at_tick is not None and at_tick > flood.tick:
            d = max(
                flood.predict_depth_at_tick(fx, fy, at_tick),
                flood.predict_depth_at_tick(tx, ty, at_tick),
            )
        else:
            d = self.edge_depth_cm(meta, flood)
        threshold = min(meta.get("closureDepthCm", 30), max_depth_cm)
        return d <= threshold

    def build_traversal_graph(
        self,
        flood: FloodSimulator,
        vehicle_mode: str,
        max_depth_cm: float,
        start_tick: int | None = None,
    ) -> nx.Graph:
        tg = nx.Graph()
        tick = start_tick if start_tick is not None else flood.tick
        for u, v, key, data in self.g.edges(keys=True, data=True):
            meta = self.edge_meta.get((u, v, key)) or self.edge_meta.get((v, u, key))
            if not meta:
                continue
            if self.edge_open(meta, flood, vehicle_mode, max_depth_cm, at_tick=tick):
                w = meta["travelTime"]
                if tg.has_edge(u, v):
                    tg[u][v]["weight"] = min(tg[u][v]["weight"], w)
                else:
                    tg.add_edge(u, v, weight=w, edgeId=meta.get("id"))
        return tg

    def edge_states(self, flood: FloodSimulator) -> list[dict[str, Any]]:
        out = []
        seen = set()
        for (u, v, key), meta in self.edge_meta.items():
            eid = meta.get("id")
            if eid in seen:
                continue
            seen.add(eid)
            d = self.edge_depth_cm(meta, flood)
            out.append({
                "id": eid,
                "depthCm": round(d, 2),
                "closedForBus": d > 25,
                "closedForTruck": d > 45,
                "water": meta.get("water", False),
            })
        return out

    def nearest_node(self, x: float, y: float) -> str | None:
        best, best_d = None, float("inf")
        for n, data in self.g.nodes(data=True):
            d = (data["x"] - x) ** 2 + (data["y"] - y) ** 2
            if d < best_d:
                best_d = d
                best = n
        return best

    def resolve_node(self, coord: list[int] | tuple[int, int] | str) -> str | None:
        """Map coordinates or node key to a graph node (snap off-network points)."""
        if isinstance(coord, str):
            if coord in self.g:
                return coord
            parts = coord.split(",")
            if len(parts) == 2:
                return self.resolve_node([int(parts[0]), int(parts[1])])
            return None
        key = _node_key(coord)
        if key in self.g:
            return key
        return self.nearest_node(float(coord[0]), float(coord[1]))
