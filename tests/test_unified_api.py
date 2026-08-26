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


def test_chennai_scenario_lists():
    scenarios = client.get("/flood/scenarios").json()["scenarios"]
    ids = {s["id"] for s in scenarios}
    assert "chennai_2015_review" in ids
    r = client.post("/flood/reset?scenarioId=chennai_2015_review")
    assert r.status_code == 200
    assert r.json()["snapshot"]["scenarioId"] == "chennai_2015_review"
