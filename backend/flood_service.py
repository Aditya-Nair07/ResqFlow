"""In-memory flood simulation sessions (deterministic, single-process demo)."""

from __future__ import annotations

from simulator.state import FloodEvacState, load_scenario

_sessions: dict[str, FloodEvacState] = {}


def get_or_create_session(scenario_id: str = "urban_flood_default") -> FloodEvacState:
    if scenario_id not in _sessions:
        _sessions[scenario_id] = FloodEvacState(load_scenario(scenario_id))
    return _sessions[scenario_id]


def reset_session(
    scenario_id: str = "urban_flood_default",
    *,
    difficulty: str = "normal",
    seed_fixtures: bool | None = None,
) -> FloodEvacState:
    state = FloodEvacState(load_scenario(scenario_id))
    from sensing.chennai_fixtures import apply_difficulty, fixture_meta, seed_chennai_reports_into_plant

    if seed_fixtures is None:
        seed_fixtures = scenario_id.startswith("chennai")
    # Chennai scenarios already seed inside FloodEvacState.__init__
    if seed_fixtures and not scenario_id.startswith("chennai"):
        state.fixture_meta = fixture_meta()
        seed_chennai_reports_into_plant(state, limit=6)
    elif scenario_id.startswith("chennai"):
        state.fixture_meta = fixture_meta()
    apply_difficulty(state, difficulty)
    _sessions[scenario_id] = state
    return state


def list_scenarios() -> list[dict[str, str]]:
    from pathlib import Path
    import json

    root = Path(__file__).resolve().parents[1] / "scenarios"
    out = []
    for p in sorted(root.glob("*.json")):
        with p.open(encoding="utf-8") as f:
            data = json.load(f)
        out.append({"id": data["id"], "name": data.get("name", data["id"])})
    return out
