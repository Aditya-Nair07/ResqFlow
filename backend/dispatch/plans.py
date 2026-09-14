"""Plan comparison strategies over authoritative Flood-GAPD / ranking / verify."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from dispatch.flood_gapd import flood_gapd_key, sort_groups
from dispatch.scoring import rank_candidate
from dispatch.verify import verify_evacuation_plan
from routing.router import find_path
from sensing.lifecycle import DISPATCHABLE


PLAN_STRATEGIES = ("FASTEST", "MAXIMUM_COVERAGE", "SAFE_AND_FAIR")

# Cap the projection so a permanently-stranded group can never loop forever.
_PROJECTION_MAX_TICKS = 160


_ELIGIBLE_STATUSES = DISPATCHABLE | {"pending", "REPORTED", "VERIFIED"}


def _eligible_groups(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Include citizen REPORTED/VERIFIED groups so public rescue requests get dispatched."""
    return [g for g in groups if g.get("status") in _ELIGIBLE_STATUSES]


STRATEGY_GOALS = {
    "FASTEST": "Reach the most urgent group first — smallest ETA wins.",
    "MAXIMUM_COVERAGE": "Rescue the largest number of people in this round.",
    "SAFE_AND_FAIR": "Balance priority and vulnerability; keep a reserve unit when possible.",
}

STRATEGY_TRADEOFFS = {
    "FASTEST": "Quickest first pickup, but leaves big groups for later rounds.",
    "MAXIMUM_COVERAGE": "Covers more people per round, but the first pickup may take longer.",
    "SAFE_AND_FAIR": "Even priority across groups; slightly fewer units deployed if a reserve is kept.",
}


def _apply_plan_to_clone(sim: Any, plan: dict[str, Any]) -> None:
    """Commit this plan's first-round assignments onto a cloned plant, using the
    same verify + actuate path as the real approve endpoint."""
    from dispatch.assign import _actuate  # local import avoids a cycle

    for a in plan.get("assignments", []):
        group = next((g for g in sim.groups if g["id"] == a["groupId"]), None)
        vehicle = next((v for v in sim.vehicles if v["id"] == a["vehicleId"]), None)
        shelter = next((s for s in sim.shelters if s["id"] == a["shelterId"]), None)
        if not group or not vehicle or not shelter or vehicle.get("status") != "available":
            continue
        path_pickup = a.get("pathPickup") or {}
        path_shelter = a.get("pathShelter") or {}
        verification = verify_evacuation_plan(
            sim, vehicle, group, shelter, path_pickup, path_shelter, skip_priority_gate=True
        )
        if sim.closed_loop and not verification["passed"]:
            continue
        shelter.setdefault("reservedCapacity", 0)
        cap_left = shelter.get("capacity", 0) - shelter.get("occupancy", 0) - shelter.get("reservedCapacity", 0)
        if cap_left < 1:
            continue
        need = group["people"] - group.get("evacuatedPeople", 0)
        planned = verification.get("load") or min(need, vehicle.get("capacity", need), cap_left)
        _actuate(sim, group, {
            "vehicle": vehicle,
            "shelter": shelter,
            "pathPickup": path_pickup,
            "pathShelter": path_shelter,
            "score": a.get("score", 0),
            "verification": {**verification, "load": planned},
        })
        group["lifecycle"] = "DISPATCHED"


def _project_full_run(base_state: Any, plan: dict[str, Any]) -> dict[str, Any]:
    """Deterministically fast-forward the *whole* run for this plan on a clone.

    The plant has no RNG, so committing this plan and pressing Run produces the
    exact number returned here — that is what the Planner headline shows.
    """
    sim = deepcopy(base_state)
    _apply_plan_to_clone(sim, plan)
    sim.running = True
    start_tick = sim.tick
    last_rescued = int(sim.metrics.get("peopleEvacuated", 0))
    stall = 0
    for _ in range(_PROJECTION_MAX_TICKS):
        busy = any(v.get("status") == "busy" for v in sim.vehicles)
        current = int(sim.metrics.get("peopleEvacuated", 0))
        if not busy and current == last_rescued:
            stall += 1
            if stall >= 2:  # no one moving and no progress → run is effectively done
                break
        else:
            stall = 0
        last_rescued = current
        sim.step_simulation(project=True)

    rescued = int(sim.metrics.get("peopleEvacuated", 0))
    stranded = sum(
        max(0, g["people"] - g.get("evacuatedPeople", 0))
        for g in sim.groups
        if g.get("status") in ("stranded", "REJECTED")
    )
    return {
        "projectedRescued": rescued,
        "projectedTicks": max(0, sim.tick - start_tick),
        "projectedStranded": stranded,
    }


def compare_plans(state: Any, ranking_method: str | None = None) -> dict[str, Any]:
    method = ranking_method or state.ranking_method
    total_waiting_people = sum(
        max(0, g.get("people", 0) - g.get("evacuatedPeople", 0))
        for g in _eligible_groups(state.groups)
    )
    total_waiting_groups = len(_eligible_groups(state.groups))
    plans = []
    for strategy in PLAN_STRATEGIES:
        plan = _build_plan(state, strategy, method)
        plan["goal"] = STRATEGY_GOALS.get(strategy, "")
        plan["tradeoff"] = STRATEGY_TRADEOFFS.get(strategy, "")
        plan["totalWaitingPeople"] = total_waiting_people
        plan["totalWaitingGroups"] = total_waiting_groups
        etas = [a.get("etaTick") for a in plan.get("assignments", []) if a.get("etaTick") is not None]
        pickups = [a.get("pathPickup", {}).get("travelTime") for a in plan.get("assignments", []) if a.get("pathPickup")]
        plan["avgEtaTicks"] = round(sum(etas) / len(etas) - state.tick, 1) if etas else None
        plan["avgPickupTicks"] = round(sum(pickups) / len(pickups), 1) if pickups else None
        plan["firstPickupTicks"] = min(pickups) if pickups else None
        plan["seatsUsed"] = sum(a.get("load") or 0 for a in plan.get("assignments", []))
        # Full-run projection — the honest "how many will actually be rescued".
        plan.update(_project_full_run(state, plan))
        plans.append(plan)
    # Recommend the plan that ultimately rescues the most people (faster wins ties).
    recommended = max(
        plans,
        key=lambda p: (
            p.get("projectedRescued") or 0,
            -(p.get("projectedTicks") or 9999),
            len(p.get("assignments") or []),
        ),
    )
    if not recommended["assignments"] and not recommended.get("projectedRescued"):
        explanation = "No safe plan right now — units are busy or every route is flooded. Press Run for a tick, then Compute again."
    else:
        explanation = (
            f"{recommended['planName'].replace('_', ' ')} rescues "
            f"{recommended.get('projectedRescued', 0)} people if you commit it and press Run."
        )
    return {
        "plans": plans,
        "recommendedPlanId": recommended["planId"],
        "explanation": explanation,
        "rankingMethod": method,
        "tick": state.tick,
        "totalWaitingPeople": total_waiting_people,
        "totalWaitingGroups": total_waiting_groups,
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
