"""NetworkX disaster knowledge graph — built from simulation snapshots."""

from __future__ import annotations

import math
from typing import Any

import networkx as nx

from schemas import IncidentSnapshot, ResourceSnapshot, SimulationSnapshot

REACH_DISTANCE = 45.0
COMPETE_DISTANCE = 28.0
SUPPORT_DISTANCE = 18.0
LOW_FUEL_THRESHOLD = 30.0


def node_id(kind: str, key: str | int) -> str:
    return f"{kind}:{key}"


def _dist(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def _midpoint(ax: float, ay: float, bx: float, by: float) -> tuple[float, float]:
    return (ax + bx) / 2, (ay + by) / 2


def _route_risk(
    ax: float, ay: float, bx: float, by: float, zones: list[dict[str, Any]]
) -> float:
    risk = 0.0
    mx, my = _midpoint(ax, ay, bx, by)
    for zone in zones:
        zx, zy = zone["x"], zone["y"]
        radius = zone.get("r", 4)
        level = zone.get("level", 50)
        dist_mid = _dist(mx, my, zx, zy)
        dist_end = _dist(bx, by, zx, zy)
        if dist_mid <= radius + 2 or dist_end <= radius + 1:
            risk = max(risk, level)
    return min(risk, 100.0)


def _in_zone(x: float, y: float, zone: dict[str, Any]) -> bool:
    return _dist(x, y, zone["x"], zone["y"]) <= zone.get("r", 4) + 1


def _can_serve(resource: ResourceSnapshot, incident: IncidentSnapshot) -> bool:
    if resource.status != "available":
        return False
    if incident.need not in resource.capabilities:
        return False
    dist = _dist(resource.x, resource.y, incident.x, incident.y)
    if dist > REACH_DISTANCE:
        return False
    fuel_cost = max(8, round(dist * 0.55))
    if resource.fuel - fuel_cost < 12:
        return False
    return True


def build_graph(snapshot: SimulationSnapshot) -> nx.MultiGraph:
    g = nx.MultiGraph()
    zones = snapshot.riskZones

    for i, base in enumerate(snapshot.bases):
        nid = node_id("base", i)
        g.add_node(
            nid,
            kind="Base",
            label=str(base.get("label", f"Base {i}")),
            x=base["x"],
            y=base["y"],
        )

    for i, zone in enumerate(zones):
        nid = node_id("risk", i)
        g.add_node(
            nid,
            kind="RiskZone",
            label=str(zone.get("label", f"Risk {i}")),
            x=zone["x"],
            y=zone["y"],
            level=zone.get("level", 50),
            r=zone.get("r", 4),
        )

    for inc in snapshot.incidents:
        nid = node_id("incident", inc.id)
        g.add_node(
            nid,
            kind="Incident",
            label=inc.type,
            need=inc.need,
            urgency=inc.urgency,
            status=inc.status,
            people=inc.people,
            x=inc.x,
            y=inc.y,
        )

    for res in snapshot.resources:
        nid = node_id("resource", res.id)
        g.add_node(
            nid,
            kind="Resource",
            label=res.type,
            status=res.status,
            fuel=res.fuel,
            capabilities=list(res.capabilities),
            x=res.x,
            y=res.y,
        )

    pending = [i for i in snapshot.incidents if i.status == "pending"]
    available = [r for r in snapshot.resources if r.status == "available"]

    for res in snapshot.resources:
        r_node = node_id("resource", res.id)
        for inc in snapshot.incidents:
            i_node = node_id("incident", inc.id)
            dist = _dist(res.x, res.y, inc.x, inc.y)
            g.add_edge(
                r_node,
                i_node,
                edge_type="DISTANCE",
                weight=dist,
                distance=round(dist, 1),
            )
            if _can_serve(res, inc):
                risk = _route_risk(res.x, res.y, inc.x, inc.y, zones)
                g.add_edge(
                    r_node,
                    i_node,
                    edge_type="CAN_REACH",
                    weight=dist,
                    distance=round(dist, 1),
                    route_risk=round(risk, 1),
                )

    for i, inc_a in enumerate(pending):
        a_node = node_id("incident", inc_a.id)
        for inc_b in pending[i + 1 :]:
            if inc_a.need != inc_b.need:
                continue
            dist = _dist(inc_a.x, inc_a.y, inc_b.x, inc_b.y)
            if dist <= COMPETE_DISTANCE:
                b_node = node_id("incident", inc_b.id)
                g.add_edge(
                    a_node,
                    b_node,
                    edge_type="COMPETES_FOR",
                    weight=dist,
                    need=inc_a.need,
                )

    for res in snapshot.resources:
        r_node = node_id("resource", res.id)
        mx, my = _midpoint(res.x, res.y, 0, 0)
        for i, zone in enumerate(zones):
            if _in_zone(res.x, res.y, zone) or _route_risk(
                res.x, res.y, mx, my, [zone]
            ) > 40:
                z_node = node_id("risk", i)
                if g.has_node(z_node):
                    g.add_edge(
                        r_node,
                        z_node,
                        edge_type="BLOCKED_BY",
                        weight=zone.get("level", 50),
                        level=zone.get("level", 50),
                    )

    for inc in snapshot.incidents:
        i_node = node_id("incident", inc.id)
        for i, zone in enumerate(zones):
            if _in_zone(inc.x, inc.y, zone):
                z_node = node_id("risk", i)
                if g.has_node(z_node):
                    g.add_edge(
                        i_node,
                        z_node,
                        edge_type="BLOCKED_BY",
                        weight=zone.get("level", 50),
                        level=zone.get("level", 50),
                    )

    for base_idx, base in enumerate(snapshot.bases):
        b_node = node_id("base", base_idx)
        bx, by = base["x"], base["y"]
        for res in snapshot.resources:
            dist = _dist(bx, by, res.x, res.y)
            if dist <= SUPPORT_DISTANCE:
                g.add_edge(
                    b_node,
                    node_id("resource", res.id),
                    edge_type="SUPPORTS",
                    weight=dist,
                    distance=round(dist, 1),
                )
        for inc in pending:
            dist = _dist(bx, by, inc.x, inc.y)
            if dist <= SUPPORT_DISTANCE * 1.5:
                g.add_edge(
                    b_node,
                    node_id("incident", inc.id),
                    edge_type="SUPPORTS",
                    weight=dist,
                    distance=round(dist, 1),
                )

    return g


def graph_stats(g: nx.MultiGraph) -> dict[str, int]:
    nodes_by_kind: dict[str, int] = {}
    edges_by_type: dict[str, int] = {}
    for _, data in g.nodes(data=True):
        kind = data.get("kind", "Unknown")
        nodes_by_kind[kind] = nodes_by_kind.get(kind, 0) + 1
    for _, _, data in g.edges(data=True):
        et = data.get("edge_type", "UNKNOWN")
        edges_by_type[et] = edges_by_type.get(et, 0) + 1
    return {
        "node_count": g.number_of_nodes(),
        "edge_count": g.number_of_edges(),
        "nodes_by_kind": nodes_by_kind,
        "edges_by_type": edges_by_type,
    }


def get_incident_subgraph(g: nx.MultiGraph, incident_id: str | int, hops: int = 2) -> dict[str, Any]:
    center = node_id("incident", incident_id)
    if center not in g:
        return {"center": center, "nodes": [], "edges": [], "summary": "Incident not in graph."}

    visited = {center}
    frontier = {center}
    for _ in range(hops):
        next_frontier: set[str] = set()
        for node in frontier:
            for neighbor in g.neighbors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    next_frontier.add(neighbor)
        frontier = next_frontier

    sub = g.subgraph(visited)
    nodes = []
    for nid, data in sub.nodes(data=True):
        nodes.append({"id": nid, **{k: v for k, v in data.items() if k != "kind"}, "kind": data.get("kind")})

    edges = []
    seen: set[tuple[str, str, str]] = set()
    for u, v, _key, data in sub.edges(keys=True, data=True):
        et = data.get("edge_type", "DISTANCE")
        sig = (u, v, et)
        if sig in seen:
            continue
        seen.add(sig)
        edges.append(
            {
                "from": u,
                "to": v,
                "type": et,
                **{k: val for k, val in data.items() if k not in ("edge_type", "weight")},
            }
        )

    kind_counts: dict[str, int] = {}
    for n in nodes:
        kind = n.get("kind", "?")
        kind_counts[kind] = kind_counts.get(kind, 0) + 1

    summary = (
        f"{hops}-hop neighborhood: "
        + ", ".join(f"{k} {v}" for k, v in sorted(kind_counts.items()))
        + f", {len(edges)} edges."
    )
    return {"center": center, "nodes": nodes, "edges": edges, "summary": summary}


def ripple_check(
    g: nx.MultiGraph, snapshot: SimulationSnapshot, resource_id: str | int, incident_id: str | int
) -> dict[str, Any]:
    resource = next((r for r in snapshot.resources if str(r.id) == str(resource_id)), None)
    incident = next((i for i in snapshot.incidents if str(i.id) == str(incident_id)), None)
    if not resource or not incident:
        return {"effects": [], "summary": "Resource or incident not found."}

    effects: list[dict[str, str]] = []
    pending = [i for i in snapshot.incidents if i.status == "pending" and str(i.id) != str(incident_id)]

    same_need = [i for i in pending if i.need == incident.need]
    for other in same_need:
        dist = _dist(other.x, other.y, incident.x, incident.y)
        if dist <= COMPETE_DISTANCE:
            effects.append(
                {
                    "type": "COMPETES_FOR",
                    "detail": f"Pending {other.type} (I{other.id}) competes for {incident.need} coverage nearby.",
                }
            )

    exclusive_matches = 0
    for other in pending:
        servers = [r for r in snapshot.resources if r.status == "available" and other.need in r.capabilities]
        nearest = min(servers, key=lambda r: _dist(r.x, r.y, other.x, other.y), default=None)
        if nearest and str(nearest.id) == str(resource_id):
            exclusive_matches += 1
    if exclusive_matches:
        effects.append(
            {
                "type": "COVERAGE_GAP",
                "detail": f"Assigning R{resource_id} leaves {exclusive_matches} pending incident(s) without their nearest capable unit.",
            }
        )

    fuel_cost = max(8, round(_dist(resource.x, resource.y, incident.x, incident.y) * 0.55))
    remaining = resource.fuel - fuel_cost
    if remaining < LOW_FUEL_THRESHOLD:
        effects.append(
            {
                "type": "FUEL_PRESSURE",
                "detail": f"Fuel drops to ~{round(remaining)}% after route — limits further deployments.",
            }
        )

    route_risk = _route_risk(resource.x, resource.y, incident.x, incident.y, snapshot.riskZones)
    if route_risk >= 55:
        for i, zone in enumerate(snapshot.riskZones):
            mx, my = _midpoint(resource.x, resource.y, incident.x, incident.y)
            if _in_zone(mx, my, zone) or _in_zone(incident.x, incident.y, zone):
                effects.append(
                    {
                        "type": "ROUTE_EXPOSURE",
                        "detail": f"Route crosses {zone.get('label', f'Risk {i}')} (level {zone.get('level', 50)}).",
                    }
                )
                break

    r_node = node_id("resource", resource_id)
    i_node = node_id("incident", incident_id)
    if g.has_edge(r_node, i_node):
        edge_dict = g.get_edge_data(r_node, i_node) or {}
        has_can_reach = any(data.get("edge_type") == "CAN_REACH" for data in edge_dict.values())
        if not has_can_reach:
            effects.append(
                {
                    "type": "REACH_WARNING",
                    "detail": "Assignment proceeds but CAN_REACH edge is weak — monitor verification.",
                }
            )

    summary = (
        f"{len(effects)} ripple effect(s) detected."
        if effects
        else "No significant ripple effects for this assignment."
    )
    return {"effects": effects, "summary": summary}


def build_evidence_path(
    g: nx.MultiGraph, snapshot: SimulationSnapshot, resource_id: str | int, incident_id: str | int
) -> dict[str, Any]:
    r_node = node_id("resource", resource_id)
    i_node = node_id("incident", incident_id)
    if r_node not in g or i_node not in g:
        return {"path": [], "edges": [], "narrative": "Nodes missing from graph."}

    resource = next(r for r in snapshot.resources if str(r.id) == str(resource_id))
    incident = next(i for i in snapshot.incidents if str(i.id) == str(incident_id))

    path_nodes = [r_node]
    edge_steps: list[dict[str, Any]] = []

    nearest_base = None
    nearest_base_dist = float("inf")
    for base_idx, base in enumerate(snapshot.bases):
        b_node = node_id("base", base_idx)
        if not g.has_node(b_node):
            continue
        dist = _dist(base["x"], base["y"], resource.x, resource.y)
        if dist < nearest_base_dist:
            nearest_base_dist = dist
            nearest_base = (b_node, base.get("label", f"Base {base_idx}"))

    if nearest_base and nearest_base_dist <= SUPPORT_DISTANCE:
        b_node, b_label = nearest_base
        path_nodes.insert(0, b_node)
        edge_steps.append(
            {"from": b_node, "to": r_node, "type": "SUPPORTS", "label": f"{b_label} supplies {resource.type}"}
        )

    risk_on_route: list[tuple[str, dict]] = []
    mx, my = _midpoint(resource.x, resource.y, incident.x, incident.y)
    for i, zone in enumerate(snapshot.riskZones):
        z_node = node_id("risk", i)
        if not g.has_node(z_node):
            continue
        if _in_zone(mx, my, zone) or _in_zone(incident.x, incident.y, zone):
            risk_on_route.append((z_node, zone))

    for z_node, zone in risk_on_route[:2]:
        prev = path_nodes[-1]
        path_nodes.append(z_node)
        edge_steps.append(
            {
                "from": prev,
                "to": z_node,
                "type": "BLOCKED_BY",
                "label": f"Route exposed to {zone.get('label', 'risk zone')}",
            }
        )

    path_nodes.append(i_node)
    edge_type = "DISTANCE"
    edge_data: dict[str, Any] = {}
    if g.has_edge(r_node, i_node):
        edge_dict = g.get_edge_data(r_node, i_node) or {}
        for data in edge_dict.values():
            if data.get("edge_type") == "CAN_REACH":
                edge_type = "CAN_REACH"
                edge_data = data
                break
        if edge_type != "CAN_REACH":
            for data in edge_dict.values():
                if data.get("edge_type") == "DISTANCE":
                    edge_data = data
                    break
    edge_steps.append(
        {
            "from": path_nodes[-2],
            "to": i_node,
            "type": edge_type,
            "label": f"{resource.type} R{resource_id} → {incident.type}",
            "distance": edge_data.get("distance"),
            "route_risk": edge_data.get("route_risk"),
        }
    )

    labels = []
    for nid in path_nodes:
        data = g.nodes[nid]
        kind = data.get("kind", "?")
        label = data.get("label", nid)
        if kind == "Resource":
            labels.append(f"R{resource_id} ({label})")
        elif kind == "Incident":
            labels.append(f"I{incident_id} ({label})")
        else:
            labels.append(str(label))

    narrative = " → ".join(labels)
    return {
        "path": path_nodes,
        "edges": edge_steps,
        "narrative": narrative,
    }


def analyze_assignment(
    snapshot: SimulationSnapshot,
    incident_id: str | int,
    resource_id: str | int | None = None,
    hops: int = 2,
) -> dict[str, Any]:
    g = build_graph(snapshot)
    stats = graph_stats(g)
    subgraph = get_incident_subgraph(g, incident_id, hops=hops)
    result: dict[str, Any] = {
        "available": True,
        "stats": stats,
        "subgraph": subgraph,
        "ripple": None,
        "evidence": None,
    }
    if resource_id is not None:
        result["ripple"] = ripple_check(g, snapshot, resource_id, incident_id)
        result["evidence"] = build_evidence_path(g, snapshot, resource_id, incident_id)
    return result


def export_graph_for_viz(
    snapshot: SimulationSnapshot,
    incident_id: str | int | None = None,
    resource_id: str | int | None = None,
    hops: int = 2,
) -> dict[str, Any]:
    """Export deduplicated nodes/edges for interactive visualization."""
    g = build_graph(snapshot)
    stats = graph_stats(g)

    nodes = []
    for nid, data in g.nodes(data=True):
        nodes.append(
            {
                "id": nid,
                "kind": data.get("kind", "Unknown"),
                "label": data.get("label", nid),
                "x": data.get("x"),
                "y": data.get("y"),
                "status": data.get("status"),
                "fuel": data.get("fuel"),
                "urgency": data.get("urgency"),
                "need": data.get("need"),
                "level": data.get("level"),
            }
        )

    edges = []
    seen: set[tuple[str, str, str]] = set()
    for u, v, _key, data in g.edges(keys=True, data=True):
        et = data.get("edge_type", "DISTANCE")
        pair = tuple(sorted([u, v]))
        sig = (pair[0], pair[1], et)
        if sig in seen:
            continue
        seen.add(sig)
        edges.append(
            {
                "from": u,
                "to": v,
                "type": et,
                "distance": data.get("distance"),
                "route_risk": data.get("route_risk"),
                "level": data.get("level"),
                "need": data.get("need"),
            }
        )

    focus: dict[str, Any] = {}
    if incident_id is not None:
        focus["subgraph"] = get_incident_subgraph(g, incident_id, hops=hops)
        if resource_id is not None:
            focus["ripple"] = ripple_check(g, snapshot, resource_id, incident_id)
            focus["evidence"] = build_evidence_path(g, snapshot, resource_id, incident_id)

    return {
        "nodes": nodes,
        "edges": edges,
        "stats": stats,
        "focus": focus,
    }
