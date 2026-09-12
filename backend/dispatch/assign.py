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

    from sensing.lifecycle import DISPATCHABLE

    # Re-open stranded leftovers only when some people were already rescued
    # (partial trip) and shelter seats remain — never abandon those lives.
    for group in state.groups:
        remaining = group["people"] - group.get("evacuatedPeople", 0)
        if (
            group.get("status") == "stranded"
            and remaining > 0
            and group.get("evacuatedPeople", 0) > 0
        ):
            seats = sum(
                max(0, s.get("capacity", 0) - s.get("occupancy", 0) - s.get("reservedCapacity", 0))
                for s in state.shelters if s.get("open", True)
            )
            if seats > 0:
                group["status"] = "pending"
                group["deadlineTick"] = max(group.get("deadlineTick", 0), state.tick + 40)

    # Assign every free unit that passes the 8-check. Priority order is
    # Flood-GAPD; unreachable groups are skipped so later groups still get help.
    free_slots = len(state.available_vehicles())
    for group in sort_groups(state.groups, tick=state.tick):
        if assigned >= free_slots:
            break
        if group["status"] not in DISPATCHABLE:
            continue
        remaining = group["people"] - group.get("evacuatedPeople", 0)
        if remaining <= 0:
            group["status"] = "evacuated"
            continue

        candidates = []
        for vehicle in state.available_vehicles():
            if group.get("requestedMode") == "water" and vehicle.get("mode") != "water":
                continue
            for shelter in state.shelters:
                if not shelter.get("open", True):
                    continue
                cap_left = (
                    shelter.get("capacity", 0)
                    - shelter.get("occupancy", 0)
                    - shelter.get("reservedCapacity", 0)
                )
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
                provisional_load = min(
                    remaining,
                    max(0, vehicle.get("capacity", 0) - vehicle.get("load", 0)),
                    cap_left,
                )
                candidates.append({
                    "vehicle": vehicle,
                    "shelter": shelter,
                    "pathPickup": path_pickup,
                    "pathShelter": path_shelter,
                    "score": score,
                    "provisionalLoad": provisional_load,
                })

        # Prefer higher score, then more lives saved this trip (partial seats).
        candidates.sort(key=lambda c: (c["score"], c["provisionalLoad"]), reverse=True)
        winner = None
        repair_note = None

        if state.closed_loop:
            for cand in candidates:
                # Priority is already enforced by iterating groups in
                # Flood-GAPD order above; skipping the gate here prevents a
                # reachable group from being starved behind a higher-priority
                # group that no free unit can currently reach.
                v = verify_evacuation_plan(
                    state, cand["vehicle"], group, cand["shelter"],
                    cand["pathPickup"], cand["pathShelter"],
                    skip_priority_gate=True,
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
    planned = winner.get("verification", {}).get("load")
    if planned is None:
        remaining = group["people"] - group.get("evacuatedPeople", 0)
        shelter = winner["shelter"]
        shelter_cap = (
            shelter.get("capacity", 0)
            - shelter.get("occupancy", 0)
            - shelter.get("reservedCapacity", 0)
        )
        planned = min(remaining, v.get("capacity", 0) - v.get("load", 0), max(0, shelter_cap))
    v["status"] = "busy"
    v["assignedGroupId"] = group["id"]
    v["targetShelterId"] = winner["shelter"]["id"]
    v["plannedLoad"] = max(1, int(planned))
    v["phase"] = "to_pickup"
    v["route"] = [{"type": "transit", "ticks": winner["pathPickup"].get("travelTime", 4)}]
    v["routeTickProgress"] = 0
    v["routeSegmentIndex"] = 0
    v["activePath"] = winner["pathPickup"]
    v["legStart"] = [v["x"], v["y"]]  # for on-map movement interpolation
    fuel_cost = winner["pathPickup"].get("travelTime", 0) * 2
    v["fuel"] = max(0, v.get("fuel", 0) - fuel_cost)
    # Reserve only the seats this trip will actually use (partial loads OK).
    shelter = winner["shelter"]
    shelter.setdefault("reservedCapacity", 0)
    shelter["reservedCapacity"] = shelter.get("reservedCapacity", 0) + v["plannedLoad"]
    state.reservations.append({
        "reservationId": f"RSV-auto-{group['id']}-{v['id']}-{state.tick}",
        "incidentId": group["id"],
        "vehicleId": v["id"],
        "shelterId": shelter["id"],
        "people": v["plannedLoad"],
        "status": "RESERVED",
        "createdAt": state.tick,
    })
    group["status"] = "assigned"
    group["assignedVehicleId"] = v["id"]
    group["assignedShelterId"] = winner["shelter"]["id"]
