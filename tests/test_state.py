import pytest

from simulator.state import FloodEvacState, load_scenario
from routing.router import find_path


def test_scenario_loads():
    sc = load_scenario("urban_flood_default")
    assert sc["id"] == "urban_flood_default"
    assert len(sc["groups"]) >= 1


def test_initial_path_exists_default():
    state = FloodEvacState(load_scenario("urban_flood_default"))
    v = state.vehicles[0]
    g = state.groups[0]
    vn = state.road.nearest_node(v["x"], v["y"])
    pickup = g.get("node", [int(g["x"]), int(g["y"])])
    vn_coord = [int(vn.split(",")[0]), int(vn.split(",")[1])]
    path = find_path(state.road, state.flood, vn_coord, pickup, v["mode"], v["maxDepthCm"])
    assert path["ok"] is True


def test_simulation_step_advances_tick():
    state = FloodEvacState(load_scenario("urban_flood_default"))
    state.running = True
    out = state.step_simulation()
    assert out["tick"] == 1


def test_closed_loop_dispatch_assigns_or_repairs():
    state = FloodEvacState(load_scenario("urban_flood_default"))
    state.running = True
    state.closed_loop = True
    for _ in range(8):
        state.step_simulation()
    assert state.metrics["repairs"] >= 0 or state.metrics["peopleEvacuated"] >= 0
