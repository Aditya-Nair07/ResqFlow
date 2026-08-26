"""Flood-GAPD priority ordering."""

from __future__ import annotations

from typing import Any

from sensing.lifecycle import DISPATCHABLE


def evacuation_band(vulnerability: int) -> int:
    if vulnerability >= 90:
        return 3
    if vulnerability >= 75:
        return 2
    if vulnerability >= 55:
        return 1
    return 0


def flood_gapd_key(group: dict[str, Any], geometry_score: float = 50.0, tick: int = 0) -> float:
    band = evacuation_band(group.get("vulnerability", 50))
    people_pressure = min(group.get("people", 0) * 4, 100)
    deadline = group.get("deadlineTick", 999)
    urgency_from_deadline = max(0, 100 - max(0, deadline - tick) * 4)
    # Trust/freshness raise evidence quality; never bypass the eight checks.
    trust = float(group.get("trust", 50))
    freshness = 100.0
    created = group.get("createdTick", tick)
    age = max(0, tick - int(created))
    if age > 12:
        freshness = max(20.0, 100.0 - age * 4)
    evidence = 0.6 * trust + 0.4 * freshness
    return (
        1000 * band
        + 0.35 * geometry_score
        + 0.30 * urgency_from_deadline
        + 0.20 * people_pressure
        + 0.15 * evidence
    )


def sort_groups(groups: list[dict[str, Any]], tick: int = 0) -> list[dict[str, Any]]:
    pending = [
        g
        for g in groups
        if g.get("status") == "pending"
        or g.get("status") in DISPATCHABLE
        or g.get("lifecycle") == "PRIORITIZED"
    ]
    # Deduplicate while preserving order preference for explicit pending
    seen: set[str] = set()
    unique = []
    for g in pending:
        gid = g.get("id")
        if gid in seen:
            continue
        seen.add(gid)
        unique.append(g)
    return sorted(unique, key=lambda g: flood_gapd_key(g, tick=tick), reverse=True)
