"""Apply citizen and operator sensing into the flood plant."""

from __future__ import annotations

from typing import Any

from sensing.lifecycle import (
    confidence_score,
    duplicate_of,
    severity_from_depth_and_people,
    transition,
    trust_for,
    utc_now,
    vulnerability_from_counts,
)


SEVERITY_DEPTH = {
    "shallow": 20.0,
    "rising": 35.0,
    "knee_deep": 55.0,
    "impassable": 90.0,
    "LOW": 20.0,
    "MEDIUM": 40.0,
    "HIGH": 60.0,
    "CRITICAL": 95.0,
}


def apply_citizen_sensing(
    state: Any,
    *,
    x: float,
    y: float,
    depth_cm: float | None = None,
    severity_label: str = "rising",
    note: str = "",
    people: int = 0,
    elderly: int = 0,
    children: int = 0,
    disabled: int = 0,
    pregnant: int = 0,
    medical: bool = False,
    mobility: str = "ambulatory",
    area: str = "",
    landmark: str = "",
    reporter: str = "resident",
    source: str = "CITIZEN",
    photo: bool = False,
    lat: float | None = None,
    lng: float | None = None,
) -> dict[str, Any]:
    """Create report + optionally group; update flood depth and edges."""
    if depth_cm is None:
        depth_cm = SEVERITY_DEPTH.get(severity_label, 35.0)

    ix, iy = int(round(x)), int(round(y))
    grid = state.flood.grid_size
    ix = max(0, min(grid - 1, ix))
    iy = max(0, min(grid - 1, iy))

    severity, sev_score, sev_reasons = severity_from_depth_and_people(
        depth_cm, people, elderly, children, disabled, pregnant, medical
    )
    conf, conf_reasons = confidence_score(
        has_location=True,
        description_len=len(note or ""),
        depth_provided=True,
        people=people,
        has_photo=photo,
        source=source,
    )
    trust = trust_for(source)
    report_id = f"R-{state.tick}-{len(state.reports) + 1}"

    # Snap to the road graph so a public pin is actually reachable.
    node = state.road.resolve_node([ix, iy])
    node_xy = [ix, iy]
    if node:
        parts = node.split(",")
        node_xy = [int(parts[0]), int(parts[1])]
        ix, iy = node_xy[0], node_xy[1]

    dup = duplicate_of(state.reports, float(ix), float(iy), state.tick)

    boost = max(18.0, min(40.0, float(depth_cm) * 0.7))
    radius = 3 if depth_cm >= 70 else 2
    flood_info = state.flood.inject_waterlogging(ix, iy, boost, radius)
    # Keep every road node bus-passable. Deep water stays on off-road cells
    # so the map shows flooding without drowning the rescue route.
    if hasattr(state, "keep_roads_serviceable"):
        state.keep_roads_serviceable(22.0)

    closed_edges: list[str] = []

    status = "DUPLICATE" if dup else "REPORTED"
    report = {
        "id": report_id,
        "kind": "citizen",
        "source": source,
        "reporter": reporter,
        "createdAt": utc_now(),
        "updatedAt": utc_now(),
        "createdTick": state.tick,
        "tick": state.tick,
        "x": float(ix),
        "y": float(iy),
        "lat": lat,
        "lng": lng,
        "area": area or f"cell ({ix},{iy})",
        "landmark": landmark,
        "depthCm": float(depth_cm),
        "people": people,
        "elderly": elderly,
        "children": children,
        "disabled": disabled,
        "pregnant": pregnant,
        "medical": medical,
        "mobility": mobility,
        "description": note,
        "note": note,
        "severity": severity,
        "severityLabel": severity_label,
        "severityScore": sev_score,
        "severityReasons": sev_reasons,
        "confidenceScore": conf,
        "confidenceReasons": conf_reasons,
        "trust": trust,
        "status": status,
        "duplicateOf": dup,
        "groupId": None,
        "message": (
            f"Citizen report: waterlogging {severity_label} at ({ix},{iy})"
            + (f" — {people} people" if people else "")
        ),
        "audit": [
            {
                "at": utc_now(),
                "action": "Report received",
                "actor": reporter,
                "detail": f"{source} waterlogging at ({ix},{iy})",
            }
        ],
        "effects": {
            "depthBoostCm": boost,
            "depthAtReport": flood_info["depthAtReport"],
            "cellsTouched": flood_info["cellsTouched"],
            "roadsForcedClosed": closed_edges,
            "groupCreated": None,
        },
    }

    group_id = None
    if people > 0 and dup:
        # Same street pin again: add people to the existing group instead of dropping the request.
        existing = next((r for r in state.reports if r.get("id") == dup), None)
        gid = existing.get("groupId") if existing else None
        group = next((g for g in state.groups if g["id"] == gid), None) if gid else None
        if not group:
            group = next(
                (g for g in state.groups if abs(g.get("x", 0) - ix) <= 1.5 and abs(g.get("y", 0) - iy) <= 1.5
                 and g.get("status") not in ("evacuated", "RESOLVED", "REJECTED")),
                None,
            )
        waiting_merge = group and group.get("status") in (
            "pending", "REPORTED", "VERIFIED", "PRIORITIZED", "REPLAN_REQUIRED",
        )
        if waiting_merge:
            group["people"] = group.get("people", 0) + people
            if note:
                group["description"] = note
                group["label"] = note.strip()[:48] or group.get("label")
            group["updatedAt"] = utc_now()
            group_id = group["id"]
            report["groupId"] = group_id
            report["status"] = "REPORTED"
            report["effects"]["groupCreated"] = group_id
            report["effects"]["mergedInto"] = group_id
            status = "REPORTED"
            report["status"] = status

    if people > 0 and not group_id:
        state.citizen_report_count += 1
        group_id = f"G-{report_id}"
        vul = vulnerability_from_counts(elderly, children, disabled, pregnant, medical)
        group = {
            "id": group_id,
            "label": (note.strip()[:48] if note else "") or landmark or f"Report @ ({ix},{iy})",
            "x": float(node_xy[0]),
            "y": float(node_xy[1]),
            "node": node_xy,
            "lat": lat,
            "lng": lng,
            "area": report["area"],
            "landmark": landmark,
            "people": people,
            "elderly": elderly,
            "children": children,
            "disabled": disabled,
            "pregnant": pregnant,
            "medical": medical,
            "vulnerability": vul,
            "mobility": mobility,
            "deadlineTick": state.tick + (60 if severity == "CRITICAL" else 80 if severity == "HIGH" else 100),
            "status": "REPORTED",
            "evacuatedPeople": 0,
            "assignedVehicleId": None,
            "assignedShelterId": None,
            "source": source,
            "trust": trust,
            "confidenceScore": conf,
            "severity": severity,
            "severityScore": sev_score,
            "severityReasons": sev_reasons,
            "confidenceReasons": conf_reasons,
            "reportId": report_id,
            "description": note,
            "createdAt": utc_now(),
            "updatedAt": utc_now(),
            "audit": list(report["audit"]),
            "gapdBand": None,
            "gapdScore": None,
        }
        state.groups.append(group)
        report["groupId"] = group_id
        report["effects"]["groupCreated"] = group_id

    state.reports.append(report)
    state.last_citizen_report = report
    state.metrics["citizenReports"] = state.metrics.get("citizenReports", 0) + 1
    state.emit_event(
        "report_received",
        {"reportId": report_id, "groupId": group_id, "status": status, "duplicateOf": dup},
    )
    if closed_edges:
        state.emit_event("road_closed", {"edges": closed_edges, "source": source})
    return report


def apply_operator_sensing(
    state: Any,
    *,
    group_id: str | None = None,
    report_id: str | None = None,
    actor: str = "operator",
    source: str = "OPERATOR",
    observed_depth_cm: float | None = None,
    road_status: str | None = None,
    road_edge_id: str | None = None,
    x: float | None = None,
    y: float | None = None,
    people_found: int | None = None,
    people_boarded: int | None = None,
    vehicle_id: str | int | None = None,
    vehicle_status: str | None = None,
    shelter_id: str | None = None,
    shelter_closed: bool | None = None,
    shelter_full: bool | None = None,
    note: str = "",
    reinforcement: bool = False,
    requested_mode: str | None = None,
    stand_down: bool = False,
) -> dict[str, Any]:
    """High-trust field/operator update; may force REPLAN_REQUIRED."""
    trust = trust_for(source)
    replan = False
    effects: dict[str, Any] = {}

    group = None
    if group_id:
        group = next((g for g in state.groups if g["id"] == group_id), None)
    if report_id and not group:
        report = next((r for r in state.reports if r["id"] == report_id), None)
        if report and report.get("groupId"):
            group = next((g for g in state.groups if g["id"] == report["groupId"]), None)

    if observed_depth_cm is not None:
        gx = int(group["x"]) if group else int(x or 0)
        gy = int(group["y"]) if group else int(y or 0)
        info = state.flood.inject_waterlogging(gx, gy, max(10.0, observed_depth_cm * 0.9), radius=1)
        effects["depth"] = info
        if group:
            group["observedDepthCm"] = observed_depth_cm
            group["trust"] = max(group.get("trust", 40), trust)
            group.setdefault("audit", []).append(
                {"at": utc_now(), "action": "Depth confirmed", "actor": actor, "detail": f"{observed_depth_cm} cm"}
            )
        replan = True

    if road_status in ("BLOCKED", "SLOW") or road_edge_id:
        edges = state.scenario.get("roadEdges", [])
        target = None
        if road_edge_id:
            target = next((e for e in edges if e.get("id") == road_edge_id), None)
        elif group:
            gx, gy = int(group["x"]), int(group["y"])
            for e in edges:
                fx, fy = e["from"]
                tx, ty = e["to"]
                if abs(fx - gx) + abs(fy - gy) <= 2 or abs(tx - gx) + abs(ty - gy) <= 2:
                    target = e
                    break
        if target:
            eid = target.get("id")
            if eid:
                state.road.forced_closed.add(eid)
            effects["roadClosed"] = eid
            if group:
                group["roadBlocked"] = True
                group.setdefault("audit", []).append(
                    {"at": utc_now(), "action": "Road blocked", "actor": actor, "detail": eid or ""}
                )
            state.emit_event("road_closed", {"edgeId": eid, "status": road_status, "source": source})
            replan = True

    if people_found is not None and group:
        group["people"] = max(group.get("people", 0), people_found)
        group.setdefault("audit", []).append(
            {"at": utc_now(), "action": "People found", "actor": actor, "detail": str(people_found)}
        )

    if people_boarded is not None and group:
        group["evacuatedPeople"] = min(group["people"], group.get("evacuatedPeople", 0) + people_boarded)
        if group["evacuatedPeople"] >= group["people"]:
            try:
                transition(group, "RESOLVED", actor, "All boarded")
            except ValueError:
                group["status"] = "evacuated"
        group.setdefault("audit", []).append(
            {"at": utc_now(), "action": "People boarded", "actor": actor, "detail": str(people_boarded)}
        )

    if vehicle_id is not None and vehicle_status:
        vehicle = next((v for v in state.vehicles if str(v["id"]) == str(vehicle_id)), None)
        if vehicle:
            if vehicle_status in ("BLOCKED", "BROKEN", "OUT_OF_SERVICE"):
                vehicle["status"] = "available" if vehicle_status == "BLOCKED" else "broken"
                vehicle["phase"] = "idle"
                vehicle["route"] = []
                gid = vehicle.get("assignedGroupId")
                if gid:
                    g = next((gg for gg in state.groups if gg["id"] == gid), None)
                    if g:
                        try:
                            transition(g, "REPLAN_REQUIRED", actor, f"Vehicle {vehicle_id} {vehicle_status}")
                        except ValueError:
                            g["status"] = "pending"
                        g["assignedVehicleId"] = None
                        g["assignedShelterId"] = None
                    vehicle["assignedGroupId"] = None
                replan = True
            effects["vehicle"] = {"id": vehicle_id, "status": vehicle_status}

    if shelter_id is not None:
        shelter = next((s for s in state.shelters if s["id"] == shelter_id), None)
        if shelter:
            if shelter_closed:
                shelter["open"] = False
                replan = True
            if shelter_full:
                shelter["occupancy"] = shelter.get("capacity", 0)
                replan = True
            effects["shelter"] = {"id": shelter_id, "open": shelter.get("open"), "occupancy": shelter.get("occupancy")}
            state.emit_event("shelter_status_changed", effects["shelter"])

    if reinforcement and group:
        extra = 8
        group["people"] = group.get("people", 0) + extra
        group["backupNeeded"] = True
        group.setdefault("audit", []).append(
            {"at": utc_now(), "action": "Crew asked for more people", "actor": actor, "detail": f"+{extra}"}
        )
        effects["peopleAdded"] = extra
        # Stay on the Run queue. Do not escalate (that hid groups from dispatch).

    if (requested_mode == "water" or (note and "boat" in note.lower())) and group:
        group["requestedMode"] = "water"
        group.setdefault("audit", []).append(
            {"at": utc_now(), "action": "Crew requested a boat", "actor": actor, "detail": note or "boat"}
        )
        effects["requestedMode"] = "water"

    if stand_down and group:
        effects["recall"] = state.recall_group(group["id"], actor=actor)
        replan = False

    if replan and group and group.get("status") in ("DISPATCHED", "IN_PROGRESS", "assigned", "RESOURCE_RESERVED"):
        try:
            transition(group, "REPLAN_REQUIRED", actor, note or "Field update invalidated plan")
        except ValueError:
            group["status"] = "REPLAN_REQUIRED"
        # Release reservation
        for s in state.shelters:
            if s.get("id") == group.get("assignedShelterId"):
                s["reservedCapacity"] = max(0, s.get("reservedCapacity", 0) - (
                    group["people"] - group.get("evacuatedPeople", 0)
                ))
        group["assignedVehicleId"] = None
        group["assignedShelterId"] = None
        state.emit_event("replan_required", {"groupId": group["id"], "reason": note or "field update"})

    update = {
        "id": f"FU-{len(state.field_updates) + 1}",
        "createdAt": utc_now(),
        "createdTick": state.tick,
        "source": source,
        "trust": trust,
        "actor": actor,
        "groupId": group["id"] if group else group_id,
        "reportId": report_id,
        "note": note,
        "replanRequired": replan,
        "effects": effects,
    }
    state.field_updates.append(update)
    state.emit_event("field_update", {"id": update["id"], "replanRequired": replan})
    return update


def verify_incident(state: Any, group_id: str, actor: str = "operator", accept: bool = True) -> dict[str, Any]:
    group = next((g for g in state.groups if g["id"] == group_id), None)
    if not group:
        raise KeyError(group_id)
    if accept:
        transition(group, "VERIFIED", actor, "Operator verified report")
        group["trust"] = max(group.get("trust", 40), trust_for("OPERATOR"))
        state.emit_event("report_verified", {"groupId": group_id})
    else:
        transition(group, "REJECTED", actor, "Operator rejected report")
        state.emit_event("report_rejected", {"groupId": group_id})
    return group


def prioritize_incident(state: Any, group_id: str, actor: str = "operator") -> dict[str, Any]:
    from dispatch.flood_gapd import evacuation_band, flood_gapd_key

    group = next((g for g in state.groups if g["id"] == group_id), None)
    if not group:
        raise KeyError(group_id)
    if group.get("status") == "REPORTED":
        transition(group, "VERIFIED", actor, "Auto-verify before prioritize")
    transition(group, "PRIORITIZED", actor, "Entered Flood-GAPD queue")
    # Map to pending for legacy dispatcher compatibility
    group["status"] = "pending"
    group["lifecycle"] = "PRIORITIZED"
    score = flood_gapd_key(group, tick=state.tick)
    group["gapdScore"] = round(score, 2)
    group["gapdBand"] = evacuation_band(group.get("vulnerability", 50))
    state.emit_event("priority_changed", {"groupId": group_id, "gapdScore": group["gapdScore"]})
    return group
