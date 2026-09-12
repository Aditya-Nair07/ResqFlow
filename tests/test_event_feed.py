"""Live ops event feed — curated plant events for the desk log."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient

from main import app  # noqa: E402
from flood_service import get_or_create_session  # noqa: E402

client = TestClient(app)
SCEN = "chennai_2015_review"


def test_unit_assigned_emitted_on_run():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    for _ in range(3):
        client.post("/flood/simulate/step", json={
            "scenarioId": SCEN, "steps": 1, "running": True,
            "rankingMethod": "hybrid", "closedLoop": True,
        })
    events = client.get(f"/flood/events?scenarioId={SCEN}").json()["events"]
    assigned = [e for e in events if e["type"] == "unit_assigned"]
    assert assigned, "expected unit_assigned in ops log events"
    payload = assigned[0]["payload"]
    assert payload.get("vehicleId") is not None
    assert payload.get("groupId")


def test_field_update_event_has_action_label():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    st = get_or_create_session(SCEN)
    gid = st.groups[0]["id"]
    r = client.post("/flood/field-updates", json={
        "scenarioId": SCEN, "groupId": gid, "source": "FIELD_TEAM",
        "actor": "field_team", "roadStatus": "BLOCKED", "note": "junction closed",
    })
    assert r.status_code == 200
    events = client.get(f"/flood/events?scenarioId={SCEN}").json()["events"]
    fu = [e for e in events if e["type"] == "field_update"]
    assert fu
    assert fu[-1]["payload"].get("action") == "road blocked"
    assert any(e["type"] == "road_closed" for e in events)


def test_snapshot_includes_recent_events():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    client.post("/flood/simulate/step", json={
        "scenarioId": SCEN, "steps": 1, "running": True,
        "rankingMethod": "hybrid", "closedLoop": True,
    })
    snap = client.get(f"/flood/snapshot?scenarioId={SCEN}").json()
    assert isinstance(snap.get("events"), list)
    assert len(snap["events"]) >= 1
