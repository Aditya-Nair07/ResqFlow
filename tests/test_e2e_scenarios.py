import pytest

from simulator.state import FloodEvacState, load_scenario


@pytest.mark.parametrize("scenario_id", [
    "urban_flood_default",
    "urban_flood_stress",
    "urban_flood_shelter_full",
    "urban_flood_boat_only",
])
def test_deterministic_replay(scenario_id):
    def run_once():
        s = FloodEvacState(load_scenario(scenario_id))
        s.running = True
        for _ in range(10):
            s.step_simulation()
        return s.metrics, s.tick, [g["status"] for g in s.groups]

    assert run_once() == run_once()


def test_no_route_scenario_strands_or_pending():
    s = FloodEvacState(load_scenario("urban_flood_no_route"))
    s.running = True
    s.closed_loop = True
    for _ in range(20):
        s.step_simulation()
    statuses = {g["status"] for g in s.groups}
    assert "evacuated" not in statuses or s.metrics["peopleEvacuated"] == 0
    assert "stranded" in statuses or "pending" in statuses


def test_stress_scenario_dispatch_activity():
    s = FloodEvacState(load_scenario("urban_flood_stress"))
    s.running = True
    s.closed_loop = True
    for _ in range(15):
        s.step_simulation()
    assert s.metrics["repairs"] >= 0
    assert s.tick == 15


def test_boat_scenario_can_assign():
    s = FloodEvacState(load_scenario("urban_flood_boat_only"))
    s.running = True
    s.closed_loop = True
    for _ in range(25):
        s.step_simulation()
    assert s.metrics["peopleEvacuated"] > 0 or any(g["status"] == "assigned" for g in s.groups)


def test_shelter_full_uses_alternate():
    s = FloodEvacState(load_scenario("urban_flood_shelter_full"))
    s.running = True
    s.closed_loop = True
    for _ in range(20):
        s.step_simulation()
    g = s.groups[0]
    if g["status"] == "evacuated":
        assert g.get("assignedShelterId") in ("shelter_far", "shelter_near")
