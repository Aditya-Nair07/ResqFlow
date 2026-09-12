"""Plan comparison strategies over authoritative Flood-GAPD / ranking / verify."""

from __future__ import annotations

from typing import Any

from dispatch.flood_gapd import flood_gapd_key, sort_groups
from dispatch.scoring import rank_candidate
from dispatch.verify import verify_evacuation_plan
from routing.router import find_path
from sensing.lifecycle import DISPATCHABLE


PLAN_STRATEGIES = ("FASTEST", "MAXIMUM_COVERAGE", "SAFE_AND_FAIR")


_ELIGIBLE_STATUSES = DISPATCHABLE | {"pending", "REPORTED", "VERIFIED"}


def _eligible_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Include citizen REPORTED/VERIFIED groups so public rescue requests get dispatched."""
    return [g for g in groups if g.get("status") in _ELIGIBLE_STATUSES]


def compare_plans(state: Any, ranking_method: str | None = None) -> dict[str, Any]:
    method = ranking_method or state.ranking_method
    plans = []
    for strategy in PLAN_STRATEGIES:
        plans.append(_build_plan(state, strategy, method))
    # Operator "Dispatch help" should send the most people, not hold a reserve
    # when that leaves waiting groups with no assignment.
    recommended = max(
        plans,
        key=lambda p: (len(p.get("assignments") or []), p.get("peopleReached") or 0),
    )
    unsafe = any(not a.get("verification", {}).get("passed", False) for a in recommended["assignments"])
    explanation = (
        "NO SAFE PLAN FOUND — units busy or routes flooded. Press Run, then Dispatch again."
        if not recommended["assignments"] or unsafe
        else f"{recommended['planName']} sends {len(recommended['assignments'])} unit(s) to waiting groups."
    )
    return {
        "plans": plans,
        "recommendedPlanId": recommended["planId"],
        "explanation": explanation,
        "rankingMethod": method,
        "tick": state.tick,
    }


def _build_plan(state: Any, strategy: str, method: str) -> dict[str, Any]:
    groups = _eligible_groups(state.groups)
    available = [v for v in state.vehicles if v.get("status") == "available"]
    # Hold a reserve only when we have spare units after covering waiters.
    reserve = 1 if strategy == "SAFE_AND_FAIR" and len(available) > max(2, len(groups)) else 0
    if strategy == "MAXIMUM_COVERAGE":
        ordered = sorted(groups, key=lambda g: g.get("people", 0), reverse=True)
    elif strategy == "FASTEST":
        ordered = sorted(groups, key=lambda g: (0 if g.get("severity") == "CRITICAL" else 1, g.get("deadlineTick", 999)))
    else:
        ordered = sort_groups(groups if all(g.get("status") == "pending" for g in groups) else [
            {**g, "status": "pending"} for g in groups
        ], tick=state.tick)

    used_vehicles: set[Any] = set()
    planned_load: dict[str, int] = {}  # shelter can serve several groups if capacity allows
    assignments = []
    rejected = []

    for group in ordered[:6]:
        remaining_slots = len(available) - len(used_vehicles)
        if remaining_slots <= reserve and strategy == "SAFE_AND_FAIR":
            rejected.append({"groupId": group["id"], "reason": "reserve capacity protected"})
            continue
        best = None
        best_score = -1e9
        for vehicle in available:
            if vehicle["id"] in used_vehicles:
                continue
            for shelter in state.shelters:
                if not shelter.get("open", True):
                    continue
                cap_left = (
                    shelter.get("capacity", 0)
                    - shelter.get("occupancy", 0)
                    - shelter.get("reservedCapacity", 0)
                    - planned_load.get(shelter["id"], 0)
                )
                need = group["people"] - group.get("evacuatedPeople", 0)
                if cap_left < min(need, 1):
                    continue
                pickup = group.get("node", [int(group["x"]), int(group["y"])])
                shelter_node = shelter.get("node", [int(shelter["x"]), int(shelter["y"])])
                vnode = state.road.resolve_node([int(vehicle["x"]), int(vehicle["y"])]) or pickup
                vn = [int(vnode.split(",")[0]), int(vnode.split(",")[1])] if isinstance(vnode, str) else pickup
                path_pickup = find_path(
                    state.road, state.flood, vn, pickup,
                    vehicle.get("mode", "road"), vehicle.get("maxDepthCm", 25),
                )
                eta = path_pickup.get("etaTick", state.tick + 10) if path_pickup.get("ok") else state.tick + 99
                path_shelter = find_path(
                    state.road, state.flood, pickup, shelter_node,
                    vehicle.get("mode", "road"), vehicle.get("maxDepthCm", 25),
                    arrival_tick=eta,
                )
                depot = state.depots[0] if state.depots else {"x": vehicle["x"], "y": vehicle["y"]}
                depth = state.flood.depth_at(group["x"], group["y"])
                score = rank_candidate(method, vehicle, group, shelter, depot, path_pickup, path_shelter, depth)
                if strategy == "FASTEST":
                    score -= path_pickup.get("travelTime", 99) * 2
                if strategy == "MAXIMUM_COVERAGE":
                    score += min(vehicle.get("capacity", 0), need)
                verification = verify_evacuation_plan(
                    state, vehicle, group, shelter, path_pickup, path_shelter, skip_priority_gate=True
                )
                if state.closed_loop and not verification["passed"]:
                    continue
                if score > best_score:
                    best_score = score
                    best = {
                        "groupId": group["id"],
                        "vehicleId": vehicle["id"],
                        "shelterId": shelter["id"],
                        "score": round(score, 2),
                        "etaTick": verification.get("etaTick"),
                        "load": verification.get("load"),
                        "verification": verification,
                        "pathPickup": path_pickup,
                        "pathShelter": path_shelter,
                        "gapd": flood_gapd_key(group, tick=state.tick),
                        "reason": f"{vehicle.get('type')} + {shelter.get('label', shelter['id'])} via {method}",
                    }
        if best:
            used_vehicles.add(best["vehicleId"])
            planned_load[best["shelterId"]] = planned_load.get(best["shelterId"], 0) + (best.get("load") or 0)
            assignments.append(best)
        else:
            rejected.append({"groupId": group["id"], "reason": "no candidate passed capacity/route/checks"})

    return {
        "planId": f"PLAN-{strategy}-{state.tick}",
        "planName": strategy,
        "rankingMethod": method,
        "tick": state.tick,
        "assignments": assignments,
        "rejected": rejected,
        "vehiclesReserved": len(assignments),
        "vehiclesLeftInReserve": max(0, len(available) - len(used_vehicles)),
        "peopleReached": sum(
            next((g["people"] for g in state.groups if g["id"] == a["groupId"]), 0) for a in assignments
        ),
    }
