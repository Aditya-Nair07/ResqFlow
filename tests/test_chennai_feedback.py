"""Chennai fixtures + difficulty rehearsal tests."""

from fastapi.testclient import TestClient

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from main import app

client = TestClient(app)


def test_chennai_fixtures_endpoint():
    r = client.get("/flood/chennai/fixtures")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["reportCount"] >= 1
    assert body["meta"]["shelterCount"] >= 1
    assert body["reports"]


def test_chennai_reset_seeds_reports_into_plant():
    r = client.post("/flood/reset?scenarioId=chennai_2015_review&difficulty=normal")
    assert r.status_code == 200
    snap = r.json()["snapshot"]
    assert snap["scenarioId"] == "chennai_2015_review"
    assert snap["fixtureMeta"]["reportCount"] >= 1
    # Scenario groups + seeded citizen reports
    assert len(snap["groups"]) > 4
    assert any(g.get("source") == "CITIZEN" for g in snap["groups"])
    assert any(g.get("area") for g in snap["groups"] if g.get("source") == "CITIZEN")


def test_difficulty_raises_rainfall():
    client.post("/flood/reset?scenarioId=chennai_2015_review&difficulty=normal")
    normal = client.get("/flood/snapshot?scenarioId=chennai_2015_review").json()["rainfallPerTick"]
    heavy = client.post("/flood/difficulty", json={
        "scenarioId": "chennai_2015_review",
        "difficulty": "heavy",
    }).json()
    assert heavy["difficulty"]["difficulty"] == "heavy"
    assert heavy["snapshot"]["rainfallPerTick"] > normal


def test_field_update_depth_and_replan_path():
    client.post("/flood/reset?scenarioId=chennai_2015_review&difficulty=normal")
    snap = client.get("/flood/snapshot?scenarioId=chennai_2015_review").json()
    gid = next(g["id"] for g in snap["groups"] if g.get("source") == "CITIZEN")
    r = client.post("/flood/field-updates", json={
        "scenarioId": "chennai_2015_review",
        "groupId": gid,
        "source": "FIELD_TEAM",
        "actor": "FIELD TEAM",
        "observedDepthCm": 95,
        "roadStatus": "BLOCKED",
        "peopleFound": 12,
        "note": "Waist deep at junction",
    })
    assert r.status_code == 200
    assert r.json()["update"]["trust"] >= 80
    events = client.get("/flood/events?scenarioId=chennai_2015_review").json()["events"]
    assert any(e["type"] in ("road_closed", "field_update", "replan_required") for e in events)
