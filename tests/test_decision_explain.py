"""Decision explainability + trust trail stamps."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient

from main import app  # noqa: E402 — load plant before dispatch package edges
from dispatch.explain import build_decision_record, method_label, rejected_from_candidate  # noqa: E402
from flood_service import get_or_create_session  # noqa: E402

client = TestClient(app)
SCEN = "chennai_2015_review"


def test_method_label_hybrid_default():
    assert "Ellipse" in method_label("hybrid")
    assert method_label("ellipse") == "Ellipse"


def test_build_decision_record_summary():
    group = {"id": "g1", "gapdScore": 2000}
    winner = {
        "vehicle": {"id": 4, "type": "Rescue Boat"},
        "shelter": {"id": "shelter_a", "label": "Velachery School Shelter"},
        "score": 88.34,
        "verification": {
            "load": 8,
            "failed": [],
            "checks": [
                {"label": "vehicle available", "passed": True},
                {"label": "pickup route exists", "passed": True},
            ],
        },
    }
    rejected = [
        rejected_from_candidate(
            {"vehicle": {"id": 1, "type": "Evacuation Bus"}, "shelter": {"id": "shelter_b"}, "score": 70},
            {"failed": ["shelter open with capacity"]},
        )
    ]
    rec = build_decision_record(group=group, winner=winner, method="hybrid", tick=3, rejected=rejected)
    assert rec["vehicleId"] == 4
    assert rec["load"] == 8
    assert rec["checksPassed"] == 2
    assert "Rescue Boat" in rec["summary"]
    assert rec["rejected"][0]["reason"] == "shelter open with capacity"
    assert "Hybrid" in rec["methodLabel"]


def test_dispatch_stamps_last_decision_and_audit():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    st = get_or_create_session(SCEN)
    # Seed groups should have a short audit trail
    assert any(g.get("audit") for g in st.groups)

    for _ in range(4):
        client.post("/flood/simulate/step", json={
            "scenarioId": SCEN, "steps": 1, "running": True,
            "rankingMethod": "hybrid", "closedLoop": True,
        })

    assigned = [g for g in st.groups if g.get("status") == "assigned" and g.get("lastDecision")]
    assert assigned, "expected at least one assigned group with lastDecision"
    g = assigned[0]
    d = g["lastDecision"]
    assert d["vehicleId"] == g["assignedVehicleId"]
    assert d["shelterId"] == g["assignedShelterId"]
    assert d["checksTotal"] >= 1
    assert any(a.get("action") == "Unit assigned" for a in g.get("audit", []))

    snap = client.get(f"/flood/snapshot?scenarioId={SCEN}").json()
    sg = next(x for x in snap["groups"] if x["id"] == g["id"])
    assert sg.get("lastDecision", {}).get("vehicleId") == g["assignedVehicleId"]
    assert any(t.get("decision") for t in snap.get("recentTraces", []) if t.get("groupId") == g["id"])


def test_field_update_appends_audit():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    st = get_or_create_session(SCEN)
    gid = st.groups[0]["id"]
    before = len(st.groups[0].get("audit") or [])
    r = client.post("/flood/field-updates", json={
        "scenarioId": SCEN, "groupId": gid, "source": "FIELD_TEAM",
        "actor": "field_team", "reinforcement": True,
    })
    assert r.status_code == 200
    g = next(x for x in st.groups if x["id"] == gid)
    assert len(g["audit"]) > before
    assert g["trust"] >= 80  # field team raises trust
