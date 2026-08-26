"""Closed-loop assignment with transactional repair."""

from __future__ import annotations

from typing import Any

from dispatch.flood_gapd import sort_groups
from dispatch.scoring import rank_candidate
from dispatch.verify import verify_evacuation_plan
from graph_store import save_trace_analysis
from routing.router import find_path


def run_dispatch_tick(state: Any) -> dict[str, Any]:
    method = state.ranking_method
    assigned = 0
    repairs = 0
    traces = []

    for group in sort_groups(state.groups, tick=state.tick)[:2]:
        if group["status"] != "pending":
            continue
        remaining = group["people"] - group.get("evacuatedPeople", 0)
        if remaining <= 0:
            group["status"] = "evacuated"
            continue

        candidates = []
        for vehicle in state.available_vehicles():
            for shelter in state.shelters:
                if not shelter.get("open", True):
                    continue
                cap_left = shelter.get("capacity", 0) - shelter.get("occupancy", 0)
                if cap_left <= 0:
                    continue
                pickup_node = group.get("node", [int(group["x"]), int(group["y"])])
                shelter_node = shelter.get("node", [int(shelter["x"]), int(shelter["y"])])
                vnode = state.road.nearest_node(vehicle["x"], vehicle["y"]) or pickup_node
                vn = [int(vnode.split(",")[0]), int(vnode.split(",")[1])] if isinstance(vnode, str) else pickup_node

                path_pickup = find_path(
                    state.road, state.flood, vn, pickup_node,
                    vehicle.get("mode", "road"), vehicle.get("maxDepthCm", 25),
                )
                eta_after_pickup = path_pickup.get("etaTick", state.tick + 10) if path_pickup.get("ok") else state.tick + 99
                path_shelter = find_path(
                    state.road, state.flood, pickup_node, shelter_node,
                    vehicle.get("mode", "road"), vehicle.get("maxDepthCm", 25),
                    arrival_tick=eta_after_pickup,
                )
                depot = state.depots[0] if state.depots else {"x": vehicle["x"], "y": vehicle["y"]}
                depth = state.flood.depth_at(group["x"], group["y"])
                score = rank_candidate(
                    method, vehicle, group, shelter, depot,
                    path_pickup, path_shelter, depth,
                )
                candidates.append({
                    "vehicle": vehicle,
                    "shelter": shelter,
                    "pathPickup": path_pickup,
                    "pathShelter": path_shelter,
                    "score": score,
                })

        candidates.sort(key=lambda c: c["score"], reverse=True)
        winner = None
        repair_note = None

        if state.closed_loop:
            for cand in candidates:
                v = verify_evacuation_plan(
                    state, cand["vehicle"], group, cand["shelter"],
                    cand["pathPickup"], cand["pathShelter"],
                )
                if v["passed"]:
                    winner = {**cand, "verification": v}
                    break
                repairs += 1
                repair_note = f"Repair: {cand['vehicle']['type']} failed — {', '.join(v['failed'])}"
        elif candidates:
            winner = {**candidates[0], "verification": {"passed": True, "checks": [], "failed": []}}
            state.metrics["unsafeActuations"] += 1

        if winner:
            _actuate(state, group, winner)
            assigned += 1
            trace = {
                "groupId": group["id"],
                "vehicleId": winner["vehicle"]["id"],
                "shelterId": winner["shelter"]["id"],
                "score": winner["score"],
                "method": method,
                "repairNote": repair_note,
                "tick": state.tick,
                "verification": winner.get("verification", {}),
            }
            state.traces.append(trace)
            traces.append(trace)
            trace_id = f"FL-{state.scenario_id}-{state.tick}-{group['id']}"
            try:
                save_trace_analysis(trace_id, {
                    "trace_id": trace_id,
                    "mode": "flood-evacuation",
                    "scenario_id": state.scenario_id,
                    "group_id": group["id"],
                    "vehicle_id": winner["vehicle"]["id"],
                    "shelter_id": winner["shelter"]["id"],
                    "tick": state.tick,
                    "snapshot": state.to_snapshot(),
                    "trace": trace,
                })
            except OSError:
                pass
        elif group.get("deadlineTick", 999) <= state.tick:
            group["status"] = "stranded"
            state.metrics["strandedGroups"] += 1

    state.metrics["repairs"] += repairs
    return {"assigned": assigned, "repairs": repairs, "traces": traces}


def _actuate(state: Any, group: dict[str, Any], winner: dict[str, Any]) -> None:
    v = winner["vehicle"]
    v["status"] = "busy"
    v["assignedGroupId"] = group["id"]
    v["targetShelterId"] = winner["shelter"]["id"]
    v["phase"] = "to_pickup"
    v["route"] = [{"type": "transit", "ticks": winner["pathPickup"].get("travelTime", 4)}]
    v["routeTickProgress"] = 0
    v["routeSegmentIndex"] = 0
    v["activePath"] = winner["pathPickup"]
    fuel_cost = winner["pathPickup"].get("travelTime", 0) * 2
    v["fuel"] = max(0, v.get("fuel", 0) - fuel_cost)
    group["status"] = "assigned"
    group["assignedVehicleId"] = v["id"]
    group["assignedShelterId"] = winner["shelter"]["id"]
