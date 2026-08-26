"""Approve and commit plan assignments with optimistic concurrency."""

from __future__ import annotations

from typing import Any

from dispatch.assign import _actuate  # type: ignore
from dispatch.verify import verify_evacuation_plan
from sensing.lifecycle import utc_now


def store_compared_plans(state: Any, compare_result: dict[str, Any]) -> dict[str, Any]:
    state.plan_version += 1
    for plan in compare_result.get("plans", []):
        plan["planVersion"] = state.plan_version
        plan["createdTick"] = state.tick
        state.proposed_plans[plan["planId"]] = plan
    compare_result["planVersion"] = state.plan_version
    state.emit_event("plan_proposed", {"planVersion": state.plan_version, "recommended": compare_result.get("recommendedPlanId")})
    return compare_result


def approve_plan(
    state: Any,
    plan_id: str,
    *,
    plan_version: int | None = None,
    tick: int | None = None,
    actor: str = "operator",
    override: bool = False,
    override_reason: str = "",
) -> dict[str, Any]:
    plan = state.proposed_plans.get(plan_id)
    if not plan:
        return {"ok": False, "error": "plan not found", "code": "PLAN_NOT_FOUND"}

    if plan_version is not None and plan.get("planVersion") != plan_version:
        return {"ok": False, "error": "stale plan version", "code": "STALE_PLAN"}
    if tick is not None and tick != state.tick:
        return {"ok": False, "error": "stale tick", "code": "STALE_TICK"}
    if plan.get("createdTick") != state.tick:
        # Allow same-tick only for closed-loop safety unless override logged
        if not override:
            return {
                "ok": False,
                "error": "plan tick no longer matches plant; re-compare",
                "code": "STALE_PLAN",
            }

    committed = []
    rejected = []
    for assignment in plan.get("assignments", []):
        group = next((g for g in state.groups if g["id"] == assignment["groupId"]), None)
        vehicle = next((v for v in state.vehicles if v["id"] == assignment["vehicleId"]), None)
        shelter = next((s for s in state.shelters if s["id"] == assignment["shelterId"]), None)
        if not group or not vehicle or not shelter:
            rejected.append({"groupId": assignment.get("groupId"), "reason": "missing entity"})
            continue

        path_pickup = assignment.get("pathPickup") or {}
        path_shelter = assignment.get("pathShelter") or {}
        verification = verify_evacuation_plan(
            state, vehicle, group, shelter, path_pickup, path_shelter, skip_priority_gate=True
        )
        if state.closed_loop and not verification["passed"]:
            if override:
                rejected.append({
                    "groupId": group["id"],
                    "reason": "override refused for failed verification",
                    "verification": verification,
                    "note": "unsafe route cannot be forced as normal dispatch",
                })
            else:
                rejected.append({"groupId": group["id"], "reason": "verification failed", "verification": verification})
            continue

        need = group["people"] - group.get("evacuatedPeople", 0)
        shelter.setdefault("reservedCapacity", 0)
        cap_left = shelter.get("capacity", 0) - shelter.get("occupancy", 0) - shelter.get("reservedCapacity", 0)
        if cap_left < min(need, 1) or vehicle.get("status") != "available":
            rejected.append({"groupId": group["id"], "reason": "capacity or vehicle unavailable at commit"})
            continue

        # Atomic reservation then actuate
        shelter["reservedCapacity"] = shelter.get("reservedCapacity", 0) + min(need, vehicle.get("capacity", need))
        winner = {
            "vehicle": vehicle,
            "shelter": shelter,
            "pathPickup": path_pickup,
            "pathShelter": path_shelter,
            "score": assignment.get("score", 0),
            "verification": verification,
        }
        try:
            _actuate(state, group, winner)
            group["lifecycle"] = "DISPATCHED"
            group.setdefault("audit", []).append(
                {"at": utc_now(), "action": "Dispatch approved", "actor": actor, "detail": plan_id}
            )
            reservation = {
                "reservationId": f"RSV-{plan_id}-{group['id']}",
                "planId": plan_id,
                "incidentId": group["id"],
                "vehicleId": vehicle["id"],
                "shelterId": shelter["id"],
                "people": min(need, vehicle.get("capacity", need)),
                "status": "RESERVED",
                "createdAt": utc_now(),
            }
            state.reservations.append(reservation)
            committed.append({"groupId": group["id"], "vehicleId": vehicle["id"], "shelterId": shelter["id"]})
        except Exception as exc:  # noqa: BLE001
            shelter["reservedCapacity"] = max(0, shelter.get("reservedCapacity", 0) - min(need, vehicle.get("capacity", need)))
            rejected.append({"groupId": group["id"], "reason": str(exc)})

    state.emit_event(
        "dispatch_approved",
        {"planId": plan_id, "committed": committed, "rejected": rejected, "override": override, "overrideReason": override_reason},
    )
    # Invalidate cached plans after commit
    state.proposed_plans.clear()
    state.plan_version += 1
    return {
        "ok": True,
        "planId": plan_id,
        "committed": committed,
        "rejected": rejected,
        "snapshot": state.to_snapshot(),
        "overrideLogged": bool(override and override_reason),
    }
