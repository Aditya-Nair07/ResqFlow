import pytest

from simulator.state import FloodEvacState, load_scenario
from routing.router import find_path
from dispatch.verify import verify_evacuation_plan
from dispatch.flood_gapd import sort_groups


def test_resolve_node_snaps_off_network():
    state = FloodEvacState(load_scenario("urban_flood_default"))
    # Group g1 node [12,10] is between road nodes
    key = state.road.resolve_node([12, 10])
    assert key is not None
    assert key in state.road.g


def test_path_after_snap():
    state = FloodEvacState(load_scenario("urban_flood_default"))
    v = state.vehicles[0]
    g = state.groups[0]
    vn = state.road.resolve_node([v["x"], v["y"]])
    pickup = g.get("node", [int(g["x"]), int(g["y"])])
    path = find_path(state.road, state.flood, vn, pickup, v["mode"], v["maxDepthCm"])
    assert path["ok"] is True


def test_flood_gapd_orders_by_vulnerability():
    state = FloodEvacState(load_scenario("urban_flood_default"))
    ordered = sort_groups(state.groups, tick=0)
    assert ordered[0]["vulnerability"] >= ordered[-1]["vulnerability"]


def test_verify_rejects_unavailable_vehicle():
    state = FloodEvacState(load_scenario("urban_flood_default"))
    v = state.vehicles[0]
    v["status"] = "busy"
    g = state.groups[0]
    s = state.shelters[0]
    result = verify_evacuation_plan(state, v, g, s, {"ok": True, "travelTime": 4}, {"ok": True, "travelTime": 4})
    assert result["passed"] is False
    assert "vehicle available" in result["failed"]
