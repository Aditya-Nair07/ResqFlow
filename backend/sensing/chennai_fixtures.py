"""Load and normalize Chennai demonstration fixtures into the flood plant."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
CHENNAI_DIR = REPO_ROOT / "data" / "chennai"

# Approximate Chennai demo bounding box → deterministic grid nodes
LAT_MIN, LAT_MAX = 12.90, 13.06
LON_MIN, LON_MAX = 80.20, 80.28

DEPTH_TO_SEVERITY = {
    "ankle-deep": "shallow",
    "knee-deep": "rising",
    "waist-deep": "knee_deep",
    "chest-deep": "impassable",
}

DIFFICULTY_RAIN = {
    "normal": 1.0,
    "heavy": 1.8,
    "crisis": 2.5,
}


def latlng_to_grid(lat: float, lon: float, grid_size: int = 25) -> tuple[int, int]:
    x = int(round((lon - LON_MIN) / (LON_MAX - LON_MIN) * (grid_size - 1)))
    y = int(round((LAT_MAX - lat) / (LAT_MAX - LAT_MIN) * (grid_size - 1)))
    return max(0, min(grid_size - 1, x)), max(0, min(grid_size - 1, y))


def load_shelter_summary() -> dict[str, Any]:
    path = CHENNAI_DIR / "chennai_shelters.csv"
    if not path.exists():
        return {"count": 0, "areas": [], "shelters": []}
    rows = []
    with path.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    areas = sorted({r.get("area", "") for r in rows if r.get("area")})
    return {
        "count": len(rows),
        "areas": areas[:8],
        "shelters": [
            {
                "id": r.get("id"),
                "name": r.get("name"),
                "area": r.get("area"),
                "capacity": int(float(r.get("total_capacity") or 0)),
                "lat": float(r.get("location_lat") or 0),
                "lon": float(r.get("location_lon") or 0),
            }
            for r in rows[:40]
        ],
    }


def load_citizen_reports() -> list[dict[str, Any]]:
    path = CHENNAI_DIR / "citizen_reports_2015.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else []


def fixture_meta() -> dict[str, Any]:
    shelters = load_shelter_summary()
    reports = load_citizen_reports()
    areas = [r.get("area", "").split(",")[0].split("(")[0].strip() for r in reports]
    areas = [a for a in areas if a][:6]
    return {
        "label": "CHENNAI 2015 FLOOD DATA",
        "note": "Demonstration fixtures from data/chennai — not live municipal sensors",
        "shelterCount": shelters["count"],
        "reportCount": len(reports),
        "areas": areas or shelters.get("areas", [])[:5],
        "provenance": "ResqFlow-main/data → data/chennai (demo / news-derived)",
    }


def seed_chennai_reports_into_plant(state: Any, limit: int = 6) -> list[dict[str, Any]]:
    """Inject historical-style citizen reports as sensing into the same plant."""
    from sensing.reports import apply_citizen_sensing

    reports = load_citizen_reports()[:limit]
    seeded = []
    grid = state.flood.grid_size
    for item in reports:
        loc = item.get("location") or {}
        lat = float(loc.get("lat") or 13.0)
        lon = float(loc.get("lon") or 80.24)
        x, y = latlng_to_grid(lat, lon, grid)
        depth_m = float(item.get("flood_depth_meters") or 0.5)
        depth_cm = depth_m * 100.0
        label = item.get("flood_depth") or "knee-deep"
        severity = DEPTH_TO_SEVERITY.get(label, "rising")
        # Demo people counts derived from depth severity (deterministic)
        people = 8 if severity == "shallow" else 14 if severity == "rising" else 20 if severity == "knee_deep" else 28
        report = apply_citizen_sensing(
            state,
            x=x,
            y=y,
            depth_cm=depth_cm,
            severity_label=severity,
            note=item.get("description") or item.get("area") or "Chennai 2015 field report",
            people=people,
            elderly=1 if severity in ("knee_deep", "impassable") else 0,
            children=2 if people >= 14 else 0,
            area=item.get("area") or "",
            landmark=item.get("landmark") or "",
            reporter="chennai_fixture",
            source="CITIZEN",
            lat=lat,
            lng=lon,
        )
        report["fixtureId"] = item.get("id")
        report["fixtureSource"] = item.get("source")
        seeded.append(report)
    state.fixture_meta = fixture_meta()
    state.emit_event("chennai_fixtures_seeded", {"count": len(seeded)})
    return seeded


def apply_difficulty(state: Any, difficulty: str) -> dict[str, Any]:
    difficulty = difficulty if difficulty in DIFFICULTY_RAIN else "normal"
    base = float(state.scenario.get("rainfallPerTick", 0.35))
    mult = DIFFICULTY_RAIN[difficulty]
    state.difficulty = difficulty
    state.flood.rainfall_per_tick = base * mult
    # Crisis tightens shelter capacity for rehearsal stress
    factor = 0.55 if difficulty == "crisis" else 1.0
    for shelter in state.shelters:
        original = shelter.get("_baseCapacity") or shelter.get("capacity", 0)
        shelter["_baseCapacity"] = original
        shelter["capacity"] = max(10, int(round(original * factor)))
    state.emit_event("difficulty_changed", {"difficulty": difficulty, "rainfallPerTick": state.flood.rainfall_per_tick})
    return {
        "difficulty": difficulty,
        "rainfallPerTick": state.flood.rainfall_per_tick,
        "shelterCapacityFactor": factor,
    }
