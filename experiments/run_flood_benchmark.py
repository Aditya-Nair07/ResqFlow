#!/usr/bin/env python3
"""Offline flood evacuation benchmarks — deterministic, no network."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND))

from simulator.state import FloodEvacState, load_scenario  # noqa: E402

SCENARIOS = [
    "urban_flood_default",
    "urban_flood_stress",
    "urban_flood_shelter_full",
    "urban_flood_boat_only",
    "urban_flood_no_route",
]
METHODS = ["weighted", "ellipse", "polygon", "hybrid"]
TICKS = 30
OUT = Path(__file__).resolve().parent / "results" / "flood_benchmark_results.csv"


def run_case(scenario_id: str, method: str, closed_loop: bool) -> dict:
    s = FloodEvacState(load_scenario(scenario_id))
    s.running = True
    s.ranking_method = method
    s.closed_loop = closed_loop
    for _ in range(TICKS):
        s.step_simulation()
    return {
        "metrics": s.metrics,
        "tick": s.tick,
        "pending": len(s.pending_groups()),
        "evacuated": sum(1 for g in s.groups if g["status"] == "evacuated"),
    }


def main() -> None:
    rows = []
    for scenario in SCENARIOS:
        for method in METHODS:
            for closed in (True, False):
                r = run_case(scenario, method, closed)
                m = r["metrics"]
                rows.append({
                    "case_id": f"{scenario}_{method}_{'closed' if closed else 'open'}",
                    "scenario": scenario,
                    "method": method,
                    "closed_loop": closed,
                    "ticks": TICKS,
                    "people_evacuated": m.get("peopleEvacuated", 0),
                    "repairs": m.get("repairs", 0),
                    "reroutes": m.get("reroutes", 0),
                    "unsafe": m.get("unsafeActuations", 0),
                    "stranded": m.get("strandedGroups", 0),
                    "pending": r["pending"],
                    "evacuated_groups": r["evacuated"],
                })

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Wrote {len(rows)} rows → {OUT}")


if __name__ == "__main__":
    main()
