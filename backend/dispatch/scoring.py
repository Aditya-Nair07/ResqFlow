"""Vehicle–group–shelter scoring (Weighted / Ellipse / Polygon / Hybrid)."""

from __future__ import annotations

import math
from typing import Any

WEIGHTS = {"distance": 0.28, "capacity": 0.24, "depth": 0.18, "fuel": 0.15, "mode": 0.15}


def _dist(a: dict, b: dict) -> float:
    return math.hypot(a["x"] - b["x"], a["y"] - b["y"])


def score_weighted(
    vehicle: dict[str, Any],
    group: dict[str, Any],
    shelter: dict[str, Any],
    path_pickup: dict[str, Any],
    path_shelter: dict[str, Any],
) -> float:
    d = path_pickup.get("travelTime", 99) + path_shelter.get("travelTime", 99)
    dist_score = max(0, 100 - d * 3)
    cap = min(vehicle.get("capacity", 1), group.get("people", 1))
    cap_score = min(100, cap / max(group.get("people", 1), 1) * 100)
    depth_pen = 0 if path_pickup.get("ok") and path_shelter.get("ok") else 40
    fuel_score = min(vehicle.get("fuel", 0), 100)
    mode_score = 100 if vehicle.get("mode") == "road" or group.get("mobility") != "wheelchair" else 70
    total = (
        WEIGHTS["distance"] * dist_score
        + WEIGHTS["capacity"] * cap_score
        + WEIGHTS["depth"] * (100 - depth_pen)
        + WEIGHTS["fuel"] * fuel_score
        + WEIGHTS["mode"] * mode_score
    )
    return round(total, 2)


def score_ellipse(vehicle: dict[str, Any], group: dict[str, Any], depot: dict[str, Any]) -> float:
    fa = {"x": depot["x"], "y": depot["y"]}
    fb = {"x": vehicle["x"], "y": vehicle["y"]}
    pt = {"x": group["x"], "y": group["y"]}
    sum_d = _dist(pt, fa) + _dist(pt, fb)
    reach = (vehicle.get("fuel", 50) / 100) * 20 * vehicle.get("speed", 1) + _dist(fa, fb) + 4
    margin = reach - sum_d
    if margin >= 0:
        return min(100, 58 + (margin / max(reach, 1)) * 42)
    return max(0, 55 - (-margin / max(reach, 1)) * 85)


def score_polygon(vehicle: dict[str, Any], group: dict[str, Any], flood_depth: float) -> float:
    radius = (vehicle.get("fuel", 50) / 100) * 14 * vehicle.get("speed", 1) + 4
    if flood_depth > vehicle.get("maxDepthCm", 25):
        radius *= 0.5
    d = _dist(vehicle, group)
    if d <= radius:
        return min(100, 62 + (radius - d) * 5)
    return max(0, 52 - (d - radius) * 4)


def score_hybrid(
    vehicle: dict[str, Any],
    group: dict[str, Any],
    shelter: dict[str, Any],
    depot: dict[str, Any],
    path_pickup: dict[str, Any],
    path_shelter: dict[str, Any],
    flood_depth: float,
) -> float:
    w = score_weighted(vehicle, group, shelter, path_pickup, path_shelter)
    e = score_ellipse(vehicle, group, depot)
    p = score_polygon(vehicle, group, flood_depth)
    return round(0.4 * w + 0.3 * e + 0.3 * p, 2)


def rank_candidate(
    method: str,
    vehicle: dict[str, Any],
    group: dict[str, Any],
    shelter: dict[str, Any],
    depot: dict[str, Any],
    path_pickup: dict[str, Any],
    path_shelter: dict[str, Any],
    flood_depth: float,
) -> float:
    if method == "weighted":
        return score_weighted(vehicle, group, shelter, path_pickup, path_shelter)
    if method == "ellipse":
        return score_ellipse(vehicle, group, depot)
    if method == "polygon":
        return score_polygon(vehicle, group, flood_depth)
    return score_hybrid(vehicle, group, shelter, depot, path_pickup, path_shelter, flood_depth)
