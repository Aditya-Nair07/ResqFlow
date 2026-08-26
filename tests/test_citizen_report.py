from fastapi.testclient import TestClient

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from main import app

client = TestClient(app)


def test_citizen_report_raises_depth():
    client.post("/flood/reset?scenarioId=urban_flood_default")
    before = client.get("/flood/snapshot?scenarioId=urban_flood_default").json()
    d0 = before["flood"]["depthCm"][10][12]
    r = client.post("/flood/report", json={
        "scenarioId": "urban_flood_default",
        "x": 12,
        "y": 10,
        "severity": "knee_deep",
        "note": "Canal Road flooding",
        "people": 0,
        "reporter": "resident",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["report"]["source"] == "CITIZEN"
    assert body["report"]["severityLabel"] == "knee_deep"
    assert body["snapshot"]["flood"]["depthCm"][10][12] > d0
    assert body["snapshot"]["lastCitizenReport"]["severityLabel"] == "knee_deep"


def test_citizen_report_can_create_group():
    client.post("/flood/reset?scenarioId=urban_flood_default")
    r = client.post("/flood/report", json={
        "scenarioId": "urban_flood_default",
        "x": 8,
        "y": 8,
        "severity": "rising",
        "people": 6,
        "note": "Market street",
    })
    assert r.status_code == 200
    groups = r.json()["snapshot"]["groups"]
    assert any(g.get("source") == "CITIZEN" and g.get("people") == 6 for g in groups)
    assert any(g.get("status") == "REPORTED" for g in groups)
