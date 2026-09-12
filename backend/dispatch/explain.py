"""Human-readable decision explanations for the Ops Desk.

Kept small and deterministic so the UI can show *why* a unit was chosen
without dumping raw scoring math.
"""

from __future__ import annotations

from typing import Any


METHOD_LABELS = {
    "weighted": "Weighted",
    "ellipse": "Ellipse",
    "polygon": "Polygon",
    "hybrid": "Hybrid (Weighted + Ellipse + Polygon)",
}


def method_label(method: str | None) -> str:
    key = (method or "hybrid").lower()
    return METHOD_LABELS.get(key, METHOD_LABELS["hybrid"])


def build_decision_record(
    *,
    group: dict[str, Any],
    winner: dict[str, Any],
    method: str,
    tick: int,
    rejected: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Compact record stamped on the group and stored in the dispatch trace."""
    vehicle = winner["vehicle"]
    shelter = winner["shelter"]
    verification = winner.get("verification") or {}
    checks = verification.get("checks") or []
    passed = sum(1 for c in checks if c.get("passed"))
    total = len(checks) or 8
    load = verification.get("load") or winner.get("provisionalLoad") or 0
    rejected = rejected or []

    summary = (
        f"{vehicle.get('type', 'Unit')} {vehicle.get('id')} → "
        f"{shelter.get('label') or shelter.get('id')} "
        f"({method_label(method)}, score {round(float(winner.get('score', 0)), 1)}, "
        f"load {load}, {passed}/{total} checks)"
    )

    return {
        "tick": tick,
        "groupId": group.get("id"),
        "vehicleId": vehicle.get("id"),
        "vehicleType": vehicle.get("type"),
        "shelterId": shelter.get("id"),
        "shelterLabel": shelter.get("label") or shelter.get("id"),
        "method": method,
        "methodLabel": method_label(method),
        "score": round(float(winner.get("score", 0)), 1),
        "load": load,
        "checksPassed": passed,
        "checksTotal": total,
        "checks": checks,
        "failed": verification.get("failed") or [],
        "gapdScore": group.get("gapdScore"),
        "summary": summary.strip(),
        "rejected": rejected[:2],
    }


def rejected_from_candidate(cand: dict[str, Any], verification: dict[str, Any]) -> dict[str, Any]:
    vehicle = cand.get("vehicle") or {}
    shelter = cand.get("shelter") or {}
    failed = verification.get("failed") or []
    return {
        "vehicleId": vehicle.get("id"),
        "vehicleType": vehicle.get("type"),
        "shelterId": shelter.get("id"),
        "score": round(float(cand.get("score", 0)), 1),
        "failed": failed,
        "reason": ", ".join(failed) if failed else "did not pass 8-check",
    }
