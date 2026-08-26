import pytest

from simulator.flood import FloodSimulator


def test_flood_advance_deterministic():
    a = FloodSimulator(10, rainfall_per_tick=0.5, low_points=[{"x": 5, "y": 5, "weight": 1}])
    b = FloodSimulator(10, rainfall_per_tick=0.5, low_points=[{"x": 5, "y": 5, "weight": 1}])
    for _ in range(5):
        a.advance()
        b.advance()
    assert a.depth_cm == b.depth_cm
    assert a.tick == 5


def test_depth_increases_with_rain():
    sim = FloodSimulator(8, rainfall_per_tick=0.4)
    d0 = sim.depth_at(4, 4)
    sim.advance()
    assert sim.depth_at(4, 4) >= d0
