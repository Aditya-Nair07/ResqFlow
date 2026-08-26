"""Mid-route validity checks and replanning."""

from __future__ import annotations

from typing import Any

from routing.router import find_path


def check_enroute_validity(state: Any, vehicle: dict[str, Any]) -> tuple[bool, str]:
    phase = vehicle.get("phase", "idle")
    if phase == "loading":
        return True, "ok"
    gid = vehicle.get("assignedGroupId")
    if not gid:
        return True, "ok"
    group = next((g for g in state.groups if g["id"] == gid), None)
    if not group:
        return False, "group_missing"

    mode = vehicle.get("mode", "road")
    max_depth = vehicle.get("maxDepthCm", 25)
    vnode = state.road.resolve_node([int(vehicle["x"]), int(vehicle["y"])])
    if not vnode:
        return False, "off_network"

    if phase == "to_pickup":
        pickup = group.get("node", [int(group["x"]), int(group["y"])])
        path = find_path(state.road, state.flood, vnode, pickup, mode, max_depth)
        if not path.get("ok"):
            return False, "route_blocked_by_flood"
        return True, "ok"

    if phase == "to_shelter":
        sid = vehicle.get("targetShelterId")
        shelter = next((s for s in state.shelters if s["id"] == sid), None)
        if not shelter:
            return False, "shelter_missing"
        if not shelter.get("open", True):
            return False, "shelter_closed"
        cap_left = shelter.get("capacity", 0) - shelter.get("occupancy", 0)
        if cap_left < vehicle.get("load", 0):
            return False, "shelter_full"
        pickup = group.get("node", [int(group["x"]), int(group["y"])])
        shelter_node = shelter.get("node", [int(shelter["x"]), int(shelter["y"])])
        path = find_path(state.road, state.flood, pickup, shelter_node, mode, max_depth)
        if not path.get("ok"):
            return False, "shelter_route_unsafe"
        return True, "ok"

    return True, "ok"


def try_reroute(state: Any, vehicle: dict[str, Any]) -> dict[str, Any]:
    """Attempt alternate route for active evacuation leg."""
    phase = vehicle.get("phase", "idle")
    gid = vehicle.get("assignedGroupId")
    if not gid or phase not in ("to_pickup", "to_shelter"):
        return {"action": "halt", "reason": "no_active_leg"}

    group = next((g for g in state.groups if g["id"] == gid), None)
    if not group:
        return {"action": "halt", "reason": "group_missing"}

    mode = vehicle.get("mode", "road")
    max_depth = vehicle.get("maxDepthCm", 25)
    start = state.road.resolve_node([int(vehicle["x"]), int(vehicle["y"])])
    if not start:
        return {"action": "halt", "reason": "off_network"}

    if phase == "to_pickup":
        goal = group.get("node", [int(group["x"]), int(group["y"])])
        path = find_path(state.road, state.flood, start, goal, mode, max_depth)
        if path.get("ok"):
            vehicle["route"] = [{"type": "transit", "ticks": path.get("travelTime", 4)}]
            vehicle["routeTickProgress"] = 0
            vehicle["activePath"] = path
            return {"action": "rerouted", "reason": "pickup_replanned", "path": path}
        return {"action": "halt", "reason": "no_safe_pickup_route"}

    sid = vehicle.get("targetShelterId")
    shelter = next((s for s in state.shelters if s["id"] == sid), None)
    if not shelter:
        return {"action": "halt", "reason": "shelter_missing"}

    # Try alternate shelter if current route unsafe
    candidates = []
    pickup = group.get("node", [int(group["x"]), int(group["y"])])
    for alt in state.shelters:
        if not alt.get("open", True):
            continue
        cap_left = alt.get("capacity", 0) - alt.get("occupancy", 0)
        if cap_left < vehicle.get("load", 0):
            continue
        shelter_node = alt.get("node", [int(alt["x"]), int(alt["y"])])
        path = find_path(state.road, state.flood, pickup, shelter_node, mode, max_depth)
        if path.get("ok"):
            candidates.append((alt, path))

    if not candidates:
        return {"action": "halt", "reason": "no_safe_shelter_route"}

    candidates.sort(key=lambda item: item[1].get("travelTime", 99))
    alt_shelter, path = candidates[0]
    vehicle["targetShelterId"] = alt_shelter["id"]
    group["assignedShelterId"] = alt_shelter["id"]
    vehicle["route"] = [{"type": "transit", "ticks": path.get("travelTime", 4)}]
    vehicle["routeTickProgress"] = 0
    vehicle["activePath"] = path
    return {
        "action": "rerouted",
        "reason": "shelter_or_route_replanned",
        "shelterId": alt_shelter["id"],
        "path": path,
    }
