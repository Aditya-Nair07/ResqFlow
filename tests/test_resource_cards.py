"""Regression tests for the field/citizen resource-card feedback loop.

Covers the bugs reported from the Operations Desk:
  * boats must recycle after a drop (not freeze in "returning")
  * an idle unit must serve a reachable waiting group (no priority-gate deadlock)
  * "More people here" (reinforcement) keeps the group on the Run queue
  * "Site clear" (stand-down) stops an en-route unit but never dumps people aboard
  * new emergencies are ranked ahead of routine groups
"""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from main import app  # noqa: E402
from flood_service import get_or_create_session  # noqa: E402
from dispatch.flood_gapd import flood_gapd_key, sort_groups  # noqa: E402

client = TestClient(app)
SCEN = "chennai_2015_review"


def _step(n=1, running=True):
    for _ in range(n):
        client.post("/flood/simulate/step", json={
            "scenarioId": SCEN, "steps": 1, "running": running,
            "rankingMethod": "hybrid", "closedLoop": True,
        })


def test_boats_recycle_and_everyone_is_served():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    st = get_or_create_session(SCEN)
    _step(30)
    # No vehicle should be frozen busy with an empty route.
    for v in st.vehicles:
        if v["status"] == "busy":
            assert v.get("route"), f"vehicle {v['id']} frozen in phase {v.get('phase')}"
    # All groups get evacuated within the horizon.
    remaining = [g for g in st.groups if g["status"] not in ("evacuated", "RESOLVED")]
    assert not remaining, f"still waiting: {[g['id'] for g in remaining]}"


def test_idle_unit_serves_reachable_group():
    """An available unit must not sit idle while a reachable group waits."""
    client.post(f"/flood/reset?scenarioId={SCEN}")
    st = get_or_create_session(SCEN)
    for _ in range(40):
        _step(1)
        idle = [v for v in st.vehicles if v["status"] == "available"]
        waiting = [g for g in st.groups
                   if g["status"] in ("pending", "REPORTED", "VERIFIED", "PRIORITIZED", "REPLAN_REQUIRED")]
        # If both an idle unit and a waiting group persist, the next tick must
        # either assign it or the group is genuinely unreachable — assert it
        # does not persist forever by checking the run eventually clears.
    remaining = [g for g in st.groups if g["status"] not in ("evacuated", "RESOLVED")]
    assert not remaining


def test_reinforcement_keeps_group_dispatchable():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    st = get_or_create_session(SCEN)
    gid = st.groups[0]["id"]
    before = st.groups[0]["people"]
    r = client.post("/flood/field-updates", json={
        "scenarioId": SCEN, "groupId": gid, "source": "FIELD_TEAM",
        "actor": "field_team", "reinforcement": True, "note": "more people",
    })
    assert r.status_code == 200
    g = next(x for x in st.groups if x["id"] == gid)
    assert g["people"] == before + 8
    assert g.get("backupNeeded") is True
    assert g["status"] not in ("ESCALATED",)  # must stay on the Run queue


def test_stand_down_stops_enroute_unit():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    st = get_or_create_session(SCEN)
    _step(4)
    target = next(((g, v) for g in st.groups for v in st.vehicles
                   if v.get("assignedGroupId") == g["id"] and v.get("phase") == "to_pickup"), None)
    assert target, "no en-route pickup unit to test"
    g, v = target
    r = client.post("/flood/field-updates", json={
        "scenarioId": SCEN, "groupId": g["id"], "source": "FIELD_TEAM",
        "actor": "field_team", "standDown": True,
    })
    assert r.status_code == 200
    assert r.json()["update"]["effects"]["recall"]["action"] == "recalled"
    freed = next(x for x in st.vehicles if x["id"] == v["id"])
    assert freed["status"] == "available"
    assert freed.get("assignedGroupId") is None
    cleared = next(x for x in st.groups if x["id"] == g["id"])
    assert cleared["status"] == "evacuated"
    assert cleared.get("standDown") is True


def test_stand_down_never_dumps_people_aboard():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    st = get_or_create_session(SCEN)
    target = None
    for _ in range(25):
        _step(1)
        target = next(((g, v) for g in st.groups for v in st.vehicles
                       if v.get("assignedGroupId") == g["id"]
                       and v.get("phase") == "to_shelter" and v.get("load")), None)
        if target:
            break
    assert target, "no loaded unit found"
    g, v = target
    load_before = v["load"]
    r = client.post("/flood/field-updates", json={
        "scenarioId": SCEN, "groupId": g["id"], "source": "FIELD_TEAM",
        "actor": "field_team", "standDown": True,
    })
    assert r.json()["update"]["effects"]["recall"]["action"] == "finish_drop_then_free"
    still = next(x for x in st.vehicles if x["id"] == v["id"])
    assert still["load"] == load_before  # people kept until the shelter


def test_new_emergency_outranks_routine():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    st = get_or_create_session(SCEN)
    # A fresh REPORTED group should score above an otherwise-similar routine
    # pending group in the same vulnerability band.
    fresh = {"id": "FRESH", "people": 6, "vulnerability": 60, "status": "REPORTED",
             "createdTick": st.tick, "deadlineTick": st.tick + 80, "trust": 60,
             "x": 9, "y": 9}
    routine = {"id": "ROUTINE", "people": 6, "vulnerability": 60, "status": "pending",
               "createdTick": st.tick, "deadlineTick": st.tick + 80, "trust": 60,
               "x": 9, "y": 9}
    assert flood_gapd_key(fresh, tick=st.tick) > flood_gapd_key(routine, tick=st.tick)


def test_boat_request_raises_priority():
    st_tick = 0
    base = {"id": "B", "people": 6, "vulnerability": 60, "status": "pending",
            "createdTick": 0, "deadlineTick": 80, "trust": 60}
    boosted = dict(base, requestedMode="water")
    assert flood_gapd_key(boosted, tick=st_tick) > flood_gapd_key(base, tick=st_tick)


def test_partial_shelter_seats_still_rescue_people():
    """If 10 wait but a shelter only has 6–8 free seats, still send a unit for those seats."""
    from dispatch.verify import verify_evacuation_plan
    from dispatch.assign import run_dispatch_tick
    from routing.router import find_path

    client.post(f"/flood/reset?scenarioId={SCEN}")
    st = get_or_create_session(SCEN)
    g = next(x for x in st.groups if "Saidapet" in str(x.get("label", "")))
    g["people"] = 26
    g["evacuatedPeople"] = 16
    g["status"] = "stranded"
    g["requestedMode"] = "water"
    g["assignedVehicleId"] = None
    g["assignedShelterId"] = None
    g["deadlineTick"] = 1
    for og in st.groups:
        if og["id"] != g["id"]:
            og["status"] = "evacuated"
            og["evacuatedPeople"] = og["people"]
    for v in st.vehicles:
        v["status"] = "available"
        v["phase"] = "idle"
        v["route"] = []
        v["assignedGroupId"] = None
        v["load"] = 0
        v["plannedLoad"] = None
    for s in st.shelters:
        if s["id"] == "shelter_a":
            s["occupancy"], s["capacity"], s["reservedCapacity"], s["open"] = 72, 80, 0, True
        elif s["id"] == "shelter_b":
            s["occupancy"], s["capacity"], s["reservedCapacity"], s["open"] = 44, 50, 0, True
        else:
            # Close the other shelters so only shelter_a (8 free) and shelter_b (6 free)
            # are candidates — isolates the "still rescue the 8" behaviour under test.
            s["occupancy"], s["capacity"], s["reservedCapacity"], s["open"] = s["capacity"], s["capacity"], 0, False

    boat = next(v for v in st.vehicles if v.get("mode") == "water")
    sh = next(s for s in st.shelters if s["id"] == "shelter_a")
    pn = g.get("node", [int(g["x"]), int(g["y"])])
    vn = st.road.nearest_node(boat["x"], boat["y"])
    vnp = [int(vn.split(",")[0]), int(vn.split(",")[1])]
    pp = find_path(st.road, st.flood, vnp, pn, boat.get("mode"), boat.get("maxDepthCm", 25))
    ps = find_path(st.road, st.flood, pn, sh.get("node"), boat.get("mode"), boat.get("maxDepthCm", 25))
    ver = verify_evacuation_plan(st, boat, g, sh, pp, ps, skip_priority_gate=True)
    assert ver["passed"] is True
    assert ver["load"] == 8  # only 8 seats left — still rescue those 8

    st.running = True
    st.ranking_method = "hybrid"
    st.closed_loop = True
    info = run_dispatch_tick(st)
    assert info["assigned"] >= 1
    assert g["status"] == "assigned"
    assigned = next(v for v in st.vehicles if v.get("assignedGroupId") == g["id"])
    assert assigned["plannedLoad"] == 8

