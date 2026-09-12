"""Planner compare / approve / reservation ledger — operator commit path."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from fastapi.testclient import TestClient

from main import app  # noqa: E402
from flood_service import get_or_create_session  # noqa: E402

client = TestClient(app)
SCEN = "chennai_2015_review"


def test_compare_returns_three_strategies():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    plans = client.post("/flood/plans/compare", json={
        "scenarioId": SCEN, "rankingMethod": "hybrid",
    }).json()
    names = {p["planName"] for p in plans["plans"]}
    # planName may be strategy label or display name — also check planId/strategy keys
    strategies = {
        p.get("strategy") or p.get("planId") or p.get("planName")
        for p in plans["plans"]
    }
    assert len(plans["plans"]) == 3
    blob = " ".join(str(x) for x in strategies | names).upper()
    assert "FASTEST" in blob
    assert "COVERAGE" in blob or "MAXIMUM" in blob
    assert "SAFE" in blob or "FAIR" in blob
    assert plans["recommendedPlanId"]
    assert plans["planVersion"] >= 1


def test_approve_commits_and_ledger_reservations():
    client.post(f"/flood/reset?scenarioId={SCEN}")
    st = get_or_create_session(SCEN)
    # Ensure free units exist (do not Run)
    for v in st.vehicles:
        assert v["status"] in ("available", "busy")

    plans = client.post("/flood/plans/compare", json={
        "scenarioId": SCEN, "rankingMethod": "hybrid",
    }).json()
    plan = next(p for p in plans["plans"] if p["planId"] == plans["recommendedPlanId"])
    assert plan.get("assignments"), "expected at least one dry assignment on fresh reset"

    snap = client.get(f"/flood/snapshot?scenarioId={SCEN}").json()
    ok = client.post(f"/flood/plans/{plans['recommendedPlanId']}/approve", json={
        "scenarioId": SCEN,
        "planId": plans["recommendedPlanId"],
        "planVersion": plans["planVersion"],
        "tick": snap["tick"],
        "actor": "operator",
    })
    assert ok.status_code == 200, ok.text
    body = ok.json()
    assert body.get("ok") is True
    assert len(body.get("committed") or []) >= 1

    snap2 = client.get(f"/flood/snapshot?scenarioId={SCEN}").json()
    reserved = [r for r in (snap2.get("reservations") or []) if r.get("status") == "RESERVED"]
    assert reserved, "ledger should show active reservations after approve"
    assert any(g.get("status") == "assigned" for g in snap2["groups"])
    assert any(v.get("status") == "busy" for v in snap2["vehicles"])


def test_operations_run_still_works_after_planner_apis():
    """Regression: closed-loop Run path untouched."""
    client.post(f"/flood/reset?scenarioId={SCEN}")
    for _ in range(3):
        client.post("/flood/simulate/step", json={
            "scenarioId": SCEN, "steps": 1, "running": True,
            "rankingMethod": "hybrid", "closedLoop": True,
        })
    snap = client.get(f"/flood/snapshot?scenarioId={SCEN}").json()
    assert any(v["status"] == "busy" for v in snap["vehicles"])
    assert any(e.get("type") == "unit_assigned" for e in snap.get("events") or [])
