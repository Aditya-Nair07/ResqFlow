"""Unified sensing, lifecycle, plans, and weather API tests."""

from fastapi.testclient import TestClient

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from main import app
from sensing.lifecycle import can_transition, trust_for

client = TestClient(app)


def test_lifecycle_transitions():
    assert can_transition("REPORTED", "VERIFIED")
    assert can_transition("VERIFIED", "PRIORITIZED")
    assert not can_transition("RESOLVED", "DISPATCHED")
    assert trust_for("OPERATOR") > trust_for("CITIZEN")


def test_citizen_to_ops_queue():
    client.post("/flood/reset?scenarioId=urban_flood_default")
    r = client.post("/flood/reports/citizen", json={
        "scenarioId": "urban_flood_default",
        "x": 12,
        "y": 10,
        "severity": "knee_deep",
        "people": 8,
        "note": "Need boats near canal",
        "elderly": 2,
    })
    assert r.status_code == 200
    report = r.json()["report"]
    assert report["status"] == "REPORTED"
    group_id = report["groupId"]
    assert group_id
    incidents = client.get("/flood/incidents?scenarioId=urban_flood_default").json()
    assert any(g["id"] == group_id for g in incidents["incidents"])


def test_verify_prioritize_compare_approve():
    client.post("/flood/reset?scenarioId=urban_flood_default")
    created = client.post("/flood/reports/citizen", json={
        "scenarioId": "urban_flood_default",
        "x": 8,
        "y": 12,
        "severity": "rising",
        "people": 10,
        "note": "Ward B",
    }).json()
    gid = created["report"]["groupId"]
    v = client.post(f"/flood/incidents/{gid}/verify", json={"scenarioId": "urban_flood_default", "accept": True})
    assert v.status_code == 200
    p = client.post(f"/flood/incidents/{gid}/prioritize", json={"scenarioId": "urban_flood_default"})
    assert p.status_code == 200
    assert p.json()["incident"]["gapdScore"] is not None

    plans = client.post("/flood/plans/compare", json={"scenarioId": "urban_flood_default", "rankingMethod": "hybrid"}).json()
    assert "plans" in plans
    assert plans["planVersion"] >= 1
    recommended = plans["recommendedPlanId"]
    # Advance tick to force stale rejection
    client.post("/flood/simulate/step", json={"scenarioId": "urban_flood_default", "steps": 1})
    stale = client.post(f"/flood/plans/{recommended}/approve", json={
        "scenarioId": "urban_flood_default",
        "planId": recommended,
        "planVersion": plans["planVersion"],
        "tick": plans["tick"],
    })
    assert stale.status_code == 409

    # Fresh compare + approve on same tick
    plans2 = client.post("/flood/plans/compare", json={"scenarioId": "urban_flood_default"}).json()
    snap = client.get("/flood/snapshot?scenarioId=urban_flood_default").json()
    ok = client.post(f"/flood/plans/{plans2['recommendedPlanId']}/approve", json={
        "scenarioId": "urban_flood_default",
        "planId": plans2["recommendedPlanId"],
        "planVersion": plans2["planVersion"],
        "tick": snap["tick"],
    })
    assert ok.status_code == 200
    assert ok.json()["ok"] is True


def test_operator_road_block_emits_replan():
    client.post("/flood/reset?scenarioId=urban_flood_default")
    r = client.post("/flood/reports/operator", json={
        "scenarioId": "urban_flood_default",
        "groupId": "g1",
        "roadStatus": "BLOCKED",
        "source": "FIELD_TEAM",
        "actor": "field",
        "note": "Bridge approach impassable",
    })
    assert r.status_code == 200
    assert r.json()["update"]["source"] == "FIELD_TEAM"
    events = client.get("/flood/events?scenarioId=urban_flood_default").json()["events"]
    assert any(e["type"] == "road_closed" for e in events)


def test_weather_fixture_fallback(monkeypatch):
    import sensing.weather as weather

    def boom(*_a, **_k):
        raise OSError("offline")

    monkeypatch.setattr(weather, "urlopen", boom)
    # Call through fixture path directly
    data = weather.fetch_open_meteo()
    assert data["provider"] in ("fixture", "open-meteo")
    assert "rainfallMmHour" in data


def test_dispatch_auto_sends_units_for_citizen_report():
    client.post("/flood/reset?scenarioId=urban_flood_default")
    created = client.post("/flood/reports/citizen", json={
        "scenarioId": "urban_flood_default",
        "x": 10,
        "y": 10,
        "severity": "knee_deep",
        "people": 9,
        "note": "Families on the underpass",
        "depthCm": 55,
    }).json()
    assert created["report"]["groupId"]
    first = client.post("/flood/dispatch/auto", json={
        "scenarioId": "urban_flood_default",
        "rankingMethod": "hybrid",
    }).json()
    assert first.get("committed"), first
    # A second public pin must still create a group and be dispatchable
    # after the first units finish (or immediately if a unit is free).
    second = client.post("/flood/reports/citizen", json={
        "scenarioId": "urban_flood_default",
        "x": 16,
        "y": 8,
        "severity": "rising",
        "people": 6,
        "note": "New street request",
        "depthCm": 40,
    }).json()
    assert second["report"]["groupId"]
    assert second["report"]["status"] in ("REPORTED", "DUPLICATE")
    snap = client.get("/flood/snapshot?scenarioId=urban_flood_default").json()
    waiting = [g for g in snap["groups"] if g["status"] in ("pending", "REPORTED", "VERIFIED", "PRIORITIZED")]
    assert waiting, snap["groups"]


def test_crew_more_people_stays_dispatchable():
    client.post("/flood/reset?scenarioId=urban_flood_default")
    before = client.get("/flood/snapshot?scenarioId=urban_flood_default").json()
    people = next(g["people"] for g in before["groups"] if g["id"] == "g1")
    r = client.post("/flood/field-updates", json={
        "scenarioId": "urban_flood_default",
        "groupId": "g1",
        "reinforcement": True,
        "source": "FIELD_TEAM",
        "note": "More people on site",
    })
    assert r.status_code == 200
    g = next(x for x in r.json()["snapshot"]["groups"] if x["id"] == "g1")
    assert g["people"] == people + 8
    assert g["status"] not in ("ESCALATED", "REJECTED")


def test_road_block_force_closes_edge():
    client.post("/flood/reset?scenarioId=urban_flood_default")
    r = client.post("/flood/field-updates", json={
        "scenarioId": "urban_flood_default",
        "groupId": "g1",
        "roadStatus": "BLOCKED",
        "source": "FIELD_TEAM",
    })
    snap = r.json()["snapshot"]
    assert snap["closedEdgeIds"]
    assert any(s.get("forcedClosed") for s in snap["roadEdgeStates"])


def test_stand_down_recalls_enroute_unit():
    client.post("/flood/reset?scenarioId=urban_flood_default")
    client.post("/flood/simulate/step", json={
        "scenarioId": "urban_flood_default",
        "steps": 1,
        "running": True,
        "rankingMethod": "hybrid",
        "closedLoop": True,
    })
    snap = client.get("/flood/snapshot?scenarioId=urban_flood_default").json()
    assigned = next((g for g in snap["groups"] if g["status"] == "assigned"), None)
    assert assigned
    r = client.post("/flood/field-updates", json={
        "scenarioId": "urban_flood_default",
        "groupId": assigned["id"],
        "standDown": True,
        "source": "OPERATOR",
        "note": "Site already clear",
    })
    assert r.status_code == 200
    after = r.json()["snapshot"]
    g = next(x for x in after["groups"] if x["id"] == assigned["id"])
    assert g["status"] == "evacuated"
    vid = assigned.get("assignedVehicleId")
    if vid is not None:
        v = next(x for x in after["vehicles"] if x["id"] == vid)
        assert v["status"] in ("available", "busy")
        if v.get("phase") != "to_shelter":
            assert v["status"] == "available"


def test_chennai_scenario_lists():
    scenarios = client.get("/flood/scenarios").json()["scenarios"]
    ids = {s["id"] for s in scenarios}
    assert "chennai_2015_review" in ids
    r = client.post("/flood/reset?scenarioId=chennai_2015_review")
    assert r.status_code == 200
    assert r.json()["snapshot"]["scenarioId"] == "chennai_2015_review"
