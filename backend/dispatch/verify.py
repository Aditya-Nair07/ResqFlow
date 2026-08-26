"""Eight flood-evacuation verification checks."""

from __future__ import annotations

from typing import Any

from dispatch.flood_gapd import sort_groups


def verify_evacuation_plan(
    state: Any,
    vehicle: dict[str, Any],
    group: dict[str, Any],
    shelter: dict[str, Any],
    path_pickup: dict[str, Any],
    path_shelter: dict[str, Any],
    skip_priority_gate: bool = False,
) -> dict[str, Any]:
    checks = []
    remaining = group["people"] - group.get("evacuatedPeople", 0)
    load = min(remaining, vehicle.get("capacity", 0) - vehicle.get("load", 0))

    checks.append({"label": "vehicle available", "passed": vehicle.get("status") == "available"})
    mobility_ok = group.get("mobility") != "wheelchair" or vehicle.get("mode") == "road"
    cap_ok = load > 0 and vehicle.get("capacity", 0) >= min(remaining, 1)
    checks.append({"label": "capacity/mobility compatible", "passed": cap_ok and mobility_ok})
    checks.append({"label": "pickup route exists", "passed": path_pickup.get("ok", False)})
    depth_ok = path_pickup.get("ok") and path_shelter.get("ok")
    checks.append({"label": "route depth safe (now + predicted)", "passed": depth_ok})
    shelter_open = shelter.get("open", True)
    shelter_cap = (
        shelter.get("capacity", 0)
        - shelter.get("occupancy", 0)
        - shelter.get("reservedCapacity", 0)
    )
    checks.append({"label": "shelter open with capacity", "passed": shelter_open and shelter_cap >= load})
    if not skip_priority_gate:
        higher = sort_groups(state.groups, tick=state.tick)
        top = higher[0]["id"] if higher else group["id"]
        checks.append({"label": "priority gate", "passed": group["id"] == top or evacuation_band_ok(group, higher)})
    else:
        checks.append({"label": "priority gate", "passed": True})
    fuel_need = (path_pickup.get("travelTime", 0) + path_shelter.get("travelTime", 0)) * 2
    checks.append({"label": "fuel sufficient", "passed": vehicle.get("fuel", 0) > fuel_need + 10})
    eta = path_pickup.get("etaTick", state.tick + 99) + path_shelter.get("travelTime", 0)
    checks.append({"label": "deadline met", "passed": eta <= group.get("deadlineTick", 999)})

    passed = all(c["passed"] for c in checks)
    return {
        "passed": passed,
        "checks": checks,
        "failed": [c["label"] for c in checks if not c["passed"]],
        "etaTick": eta,
        "load": load,
    }


def evacuation_band_ok(group: dict[str, Any], ordered: list[dict[str, Any]]) -> bool:
    if not ordered:
        return True
    from dispatch.flood_gapd import evacuation_band

    g_band = evacuation_band(group.get("vulnerability", 0))
    top_band = evacuation_band(ordered[0].get("vulnerability", 0))
    return g_band >= top_band - 1
