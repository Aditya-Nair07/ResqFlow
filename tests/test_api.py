import pytest
from fastapi.testclient import TestClient

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from main import app

client = TestClient(app)


def test_health_flood_mode():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["mode"] == "flood-evacuation"


def test_flood_scenarios_list():
    r = client.get("/flood/scenarios")
    assert r.status_code == 200
    assert len(r.json()["scenarios"]) >= 2


def test_flood_reset_and_step():
    client.post("/flood/reset?scenarioId=urban_flood_default")
    r = client.post("/flood/simulate/step", json={"scenarioId": "urban_flood_default", "steps": 3, "running": True})
    assert r.status_code == 200
    snap = r.json()["snapshot"]
    assert snap["tick"] == 3
