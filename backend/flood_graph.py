"""NetworkX evidence graph for flood evacuation assignments."""

from __future__ import annotations

from typing import Any

import networkx as nx


def build_flood_evidence_graph(snapshot: dict[str, Any]) -> nx.MultiGraph:
    g = nx.MultiGraph()
    for s in snapshot.get("shelters", []):
        nid = f"shelter:{s['id']}"
        g.add_node(nid, kind="Shelter", label=s.get("label", s["id"]), **s)
    for grp in snapshot.get("groups", []):
        nid = f"group:{grp['id']}"
        g.add_node(nid, kind="EvacGroup", label=grp.get("label", grp["id"]), **grp)
    for v in snapshot.get("vehicles", []):
        nid = f"vehicle:{v['id']}"
        g.add_node(nid, kind="Vehicle", label=v.get("type", ""), **v)
    for grp in snapshot.get("groups", []):
        if grp.get("assignedVehicleId"):
            g.add_edge(
                f"vehicle:{grp['assignedVehicleId']}",
                f"group:{grp['id']}",
                type="CAN_EVACUATE",
            )
        if grp.get("assignedShelterId"):
            g.add_edge(
                f"group:{grp['id']}",
                f"shelter:{grp['assignedShelterId']}",
                type="DELIVERS_TO",
            )
    pending = [x for x in snapshot.get("groups", []) if x.get("status") == "pending"]
    if len(pending) > 1:
        for i, a in enumerate(pending):
            for b in pending[i + 1 :]:
                g.add_edge(f"group:{a['id']}", f"group:{b['id']}", type="COMPETES_FOR")
    for edge in snapshot.get("roadEdgeStates", []):
        if edge.get("closedForBus"):
            block = f"block:{edge['id']}"
            g.add_node(block, kind="RoadBlock", label=edge["id"], depthCm=edge.get("depthCm"))
            for grp in snapshot.get("groups", []):
                if grp.get("status") in ("pending", "assigned"):
                    g.add_edge(block, f"group:{grp['id']}", type="ROUTE_BLOCKED_BY")
    return g


def analyze_flood_assignment(snapshot: dict[str, Any], group_id: str, vehicle_id: str | int | None = None) -> dict[str, Any]:
    g = build_flood_evidence_graph(snapshot)
    gid = f"group:{group_id}"
    if gid not in g:
        return {"available": False, "stats": {}, "evidence": None, "ripple": None}
    group = next((x for x in snapshot.get("groups", []) if x["id"] == group_id), None)
    narrative = []
    if group and group.get("assignedVehicleId"):
        narrative.append(f"Vehicle {group['assignedVehicleId']} assigned to evacuate {group.get('label', group_id)}.")
    if group and group.get("assignedShelterId"):
        narrative.append(f"Destination shelter: {group['assignedShelterId']}.")
    closed = [e for e in snapshot.get("roadEdgeStates", []) if e.get("closedForBus")]
    if closed:
        narrative.append(f"{len(closed)} road segment(s) closed by flood depth.")
    ripple = {
        "competingGroups": len([x for x in snapshot.get("groups", []) if x.get("status") == "pending"]),
        "shelterPressure": [
            {"id": s["id"], "remaining": s.get("capacity", 0) - s.get("occupancy", 0)}
            for s in snapshot.get("shelters", [])
        ],
        "fuelPressure": [
            {"id": v["id"], "fuel": v.get("fuel", 0)}
            for v in snapshot.get("vehicles", [])
            if v.get("status") == "available"
        ],
    }
    nodes = [{"id": n, **data} for n, data in g.nodes(data=True)]
    edges = [{"source": u, "target": v, **data} for u, v, data in g.edges(data=True)]
    return {
        "available": True,
        "stats": {"nodes": len(nodes), "edges": len(edges)},
        "evidence": {"narrative": " ".join(narrative), "nodes": nodes[:24], "edges": edges[:24]},
        "ripple": ripple,
    }
