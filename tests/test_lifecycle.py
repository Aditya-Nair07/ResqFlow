"""Unit tests for lifecycle helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sensing.lifecycle import can_transition, confidence_score, duplicate_of, severity_from_depth_and_people, trust_for


def test_trust_ordering():
    assert trust_for("OPERATOR") > trust_for("WARD_VOLUNTEER") > trust_for("CITIZEN")


def test_severity_and_confidence():
    sev, score, reasons = severity_from_depth_and_people(100, 40, elderly=5, medical=True)
    assert sev == "CRITICAL"
    assert score >= 70
    assert reasons
    conf, creasons = confidence_score(
        has_location=True, description_len=40, depth_provided=True, people=10, has_photo=True, source="OPERATOR"
    )
    assert conf >= 80
    assert creasons


def test_duplicate_detection():
    existing = [{"id": "R1", "x": 10, "y": 10, "createdTick": 1, "status": "REPORTED"}]
    assert duplicate_of(existing, 10.5, 10.2, tick=2) == "R1"
    assert duplicate_of(existing, 20, 20, tick=2) is None


def test_terminal_states():
    assert not can_transition("REJECTED", "VERIFIED")
    assert can_transition("REPORTED", "DUPLICATE")
