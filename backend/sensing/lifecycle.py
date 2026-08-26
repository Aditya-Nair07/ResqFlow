"""Canonical lifecycle, trust model, and report helpers for unified ResQFlow-Flood."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


ReportSource = str
LifecycleStatus = str

SOURCES = (
    "CITIZEN",
    "WARD_VOLUNTEER",
    "FIELD_TEAM",
    "OPERATOR",
    "PUBLIC_WEATHER_API",
    "SIMULATOR",
)

# Trust is separate from severity. High trust never bypasses the eight checks.
SOURCE_TRUST: dict[str, int] = {
    "CITIZEN": 40,
    "WARD_VOLUNTEER": 65,
    "FIELD_TEAM": 85,
    "OPERATOR": 95,
    "PUBLIC_WEATHER_API": 70,
    "SIMULATOR": 80,
}

LIFECYCLE = (
    "REPORTED",
    "VERIFIED",
    "PRIORITIZED",
    "PLAN_PROPOSED",
    "RESOURCE_RESERVED",
    "DISPATCHED",
    "IN_PROGRESS",
    "REPLAN_REQUIRED",
    "RESOLVED",
    "REJECTED",
    "DUPLICATE",
    "STRANDED",
    "ESCALATED",
    # Compat with older plant statuses used by the simulator:
    "pending",
    "assigned",
    "evacuated",
    "stranded",
)

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "REPORTED": {"VERIFIED", "REJECTED", "DUPLICATE", "ESCALATED", "pending"},
    "VERIFIED": {"PRIORITIZED", "REJECTED", "DUPLICATE", "ESCALATED"},
    "PRIORITIZED": {"PLAN_PROPOSED", "RESOURCE_RESERVED", "DISPATCHED", "ESCALATED", "pending"},
    "PLAN_PROPOSED": {"RESOURCE_RESERVED", "REJECTED", "PRIORITIZED"},
    "RESOURCE_RESERVED": {"DISPATCHED", "REJECTED", "REPLAN_REQUIRED"},
    "DISPATCHED": {"IN_PROGRESS", "REPLAN_REQUIRED", "assigned"},
    "IN_PROGRESS": {"REPLAN_REQUIRED", "RESOLVED", "STRANDED"},
    "REPLAN_REQUIRED": {"PRIORITIZED", "ESCALATED", "pending", "PLAN_PROPOSED"},
    "RESOLVED": set(),
    "REJECTED": set(),
    "DUPLICATE": set(),
    "STRANDED": {"ESCALATED"},
    "ESCALATED": set(),
    "pending": {"assigned", "DISPATCHED", "STRANDED", "stranded", "evacuated", "PRIORITIZED", "REPLAN_REQUIRED"},
    "assigned": {"IN_PROGRESS", "evacuated", "pending", "REPLAN_REQUIRED", "STRANDED"},
    "evacuated": {"RESOLVED"},
    "stranded": {"ESCALATED", "pending"},
}

# Statuses that still compete for vehicles in Flood-GAPD.
DISPATCHABLE = {"pending", "PRIORITIZED", "PLAN_PROPOSED", "REPLAN_REQUIRED"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def trust_for(source: str) -> int:
    return SOURCE_TRUST.get(source, 40)


def can_transition(current: str, new: str) -> bool:
    if current == new:
        return True
    return new in ALLOWED_TRANSITIONS.get(current, set())


def transition(entity: dict[str, Any], new_status: str, actor: str, detail: str) -> dict[str, Any]:
    current = entity.get("status", "REPORTED")
    if not can_transition(current, new_status):
        raise ValueError(f"Invalid transition: {current} -> {new_status}")
    entity["status"] = new_status
    entity["updatedAt"] = utc_now()
    entity.setdefault("audit", []).append(
        {"at": utc_now(), "action": f"Status -> {new_status}", "actor": actor, "detail": detail}
    )
    return entity


def severity_from_depth_and_people(
    depth_cm: float,
    people: int,
    elderly: int = 0,
    children: int = 0,
    disabled: int = 0,
    pregnant: int = 0,
    medical: bool = False,
) -> tuple[str, int, list[str]]:
    score = 0
    reasons: list[str] = []
    if depth_cm >= 100:
        score += 35
        reasons.append("Water depth is at least 1 metre")
    elif depth_cm >= 60:
        score += 25
        reasons.append("Water depth is at least 0.6 metres")
    elif depth_cm >= 30:
        score += 15
        reasons.append("Water depth exceeds 0.3 metres")
    vulnerable = elderly + children + disabled + pregnant
    if vulnerable >= 10:
        score += 30
        reasons.append("Large number of vulnerable people")
    elif vulnerable > 0:
        score += 15
        reasons.append("Vulnerable people are present")
    if medical:
        score += 35
        reasons.append("Medical emergency reported")
    if people >= 30:
        score += 25
        reasons.append("Large affected population")
    elif people >= 10:
        score += 15
        reasons.append("More than ten people affected")
    severity = "CRITICAL" if score >= 70 else "HIGH" if score >= 50 else "MEDIUM" if score >= 25 else "LOW"
    return severity, score, reasons


def confidence_score(
    *,
    has_location: bool,
    description_len: int,
    depth_provided: bool,
    people: int,
    has_photo: bool,
    source: str,
) -> tuple[int, list[str]]:
    score = 40
    reasons: list[str] = []
    if has_location:
        score += 15
        reasons.append("Exact location provided")
    if description_len >= 20:
        score += 10
        reasons.append("Description provided")
    if depth_provided:
        score += 10
        reasons.append("Water depth provided")
    if people > 0:
        score += 10
        reasons.append("Population estimate provided")
    if has_photo:
        score += 10
        reasons.append("Photo attached")
    if source in ("WARD_VOLUNTEER", "FIELD_TEAM", "OPERATOR"):
        score += 10
        reasons.append("Reported by a field-linked source")
    return min(score, 100), reasons


def vulnerability_from_counts(elderly: int, children: int, disabled: int, pregnant: int, medical: bool) -> int:
    base = 55 + elderly * 4 + children * 3 + disabled * 5 + pregnant * 4
    if medical:
        base += 15
    return min(100, base)


def is_stale(report: dict[str, Any], current_tick: int, max_age_ticks: int = 12) -> bool:
    created = report.get("createdTick", current_tick)
    return current_tick - int(created) > max_age_ticks


def duplicate_of(existing: list[dict[str, Any]], x: float, y: float, tick: int, radius: float = 1.5) -> str | None:
    for item in existing:
        if item.get("status") in ("REJECTED", "DUPLICATE", "RESOLVED"):
            continue
        if abs(float(item.get("x", 0)) - x) <= radius and abs(float(item.get("y", 0)) - y) <= radius:
            if tick - int(item.get("createdTick", tick)) <= 8:
                return item.get("id")
    return None
