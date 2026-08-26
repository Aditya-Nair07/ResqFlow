"""Grid water-depth progression — deterministic, no RNG."""

from __future__ import annotations

import math
from typing import Any


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


class FloodSimulator:
    """Cell-based depth field with rainfall, drain, and spread from low points."""

    def __init__(
        self,
        grid_size: int,
        rainfall_per_tick: float = 0.3,
        drain_rate: float = 0.02,
        depth_spread: float = 0.1,
        low_points: list[dict[str, Any]] | None = None,
    ):
        self.grid_size = grid_size
        self.rainfall_per_tick = rainfall_per_tick
        self.drain_rate = drain_rate
        self.depth_spread = depth_spread
        self.low_points = low_points or []
        self.tick = 0
        self.depth_cm: list[list[float]] = [
            [0.0 for _ in range(grid_size)] for _ in range(grid_size)
        ]

    def depth_at(self, x: float, y: float) -> float:
        """Bilinear sample depth at world coordinate."""
        gx = _clamp(x, 0, self.grid_size - 1.001)
        gy = _clamp(y, 0, self.grid_size - 1.001)
        x0, y0 = int(gx), int(gy)
        x1 = min(x0 + 1, self.grid_size - 1)
        y1 = min(y0 + 1, self.grid_size - 1)
        tx, ty = gx - x0, gy - y0
        d00 = self.depth_cm[y0][x0]
        d10 = self.depth_cm[y0][x1]
        d01 = self.depth_cm[y1][x0]
        d11 = self.depth_cm[y1][x1]
        return (1 - tx) * (1 - ty) * d00 + tx * (1 - ty) * d10 + (1 - tx) * ty * d01 + tx * ty * d11

    def depth_at_cell(self, cx: int, cy: int) -> float:
        if 0 <= cx < self.grid_size and 0 <= cy < self.grid_size:
            return self.depth_cm[cy][cx]
        return 0.0

    def depth_at_node(self, node: list[int] | tuple[int, int]) -> float:
        return self.depth_at_cell(int(node[0]), int(node[1]))

    def predict_depth_at_tick(self, x: float, y: float, future_tick: int) -> float:
        """Linear extrapolation from current rainfall rate (demo predictor)."""
        current = self.depth_at(x, y)
        delta_ticks = max(0, future_tick - self.tick)
        return current + delta_ticks * self.rainfall_per_tick * 0.85

    def advance(self, extra_rain: float | None = None) -> dict[str, Any]:
        rain = extra_rain if extra_rain is not None else self.rainfall_per_tick
        n = self.grid_size
        new_depth = [[0.0 for _ in range(n)] for _ in range(n)]

        for y in range(n):
            for x in range(n):
                base = self.depth_cm[y][x]
                base += rain
                for lp in self.low_points:
                    lx, ly = lp["x"], lp["y"]
                    w = lp.get("weight", 1.0)
                    dist = math.hypot(x - lx, y - ly)
                    if dist < 6:
                        base += w * self.depth_spread * max(0, 6 - dist) / 6
                neighbors = []
                for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < n and 0 <= ny < n:
                        neighbors.append(self.depth_cm[ny][nx])
                if neighbors:
                    avg_n = sum(neighbors) / len(neighbors)
                    base += self.depth_spread * (avg_n - base) * 0.35
                base = max(0.0, base - self.drain_rate)
                new_depth[y][x] = _clamp(base, 0.0, 250.0)

        self.depth_cm = new_depth
        self.tick += 1
        flooded_cells = sum(1 for row in self.depth_cm for d in row if d >= 30)
        return {
            "tick": self.tick,
            "maxDepthCm": max(max(row) for row in self.depth_cm),
            "floodedCells": flooded_cells,
        }

    def inject_waterlogging(
        self,
        x: int,
        y: int,
        depth_boost_cm: float,
        radius: int = 1,
    ) -> dict[str, Any]:
        """Citizen/operator report: raise depth around a cell (software sensor)."""
        n = self.grid_size
        cx = int(_clamp(x, 0, n - 1))
        cy = int(_clamp(y, 0, n - 1))
        touched = 0
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if dx * dx + dy * dy > radius * radius:
                    continue
                nx, ny = cx + dx, cy + dy
                if 0 <= nx < n and 0 <= ny < n:
                    falloff = 1.0 - (math.hypot(dx, dy) / (radius + 0.01)) * 0.4
                    self.depth_cm[ny][nx] = _clamp(
                        self.depth_cm[ny][nx] + depth_boost_cm * falloff,
                        0.0,
                        250.0,
                    )
                    touched += 1
        return {
            "cell": [cx, cy],
            "depthAtReport": round(self.depth_cm[cy][cx], 2),
            "cellsTouched": touched,
            "maxDepthCm": max(max(row) for row in self.depth_cm),
        }

    def to_dict(self) -> dict[str, Any]:
        max_d = max((max(row) for row in self.depth_cm), default=0.0)
        flooded = sum(1 for row in self.depth_cm for d in row if d >= 30)
        return {
            "tick": self.tick,
            "gridSize": self.grid_size,
            "depthCm": self.depth_cm,
            "rainfallPerTick": self.rainfall_per_tick,
            "maxDepthCm": max_d,
            "floodedCells": flooded,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FloodSimulator:
        sim = cls(
            grid_size=data["gridSize"],
            rainfall_per_tick=data.get("rainfallPerTick", 0.3),
        )
        sim.tick = data.get("tick", 0)
        sim.depth_cm = data.get("depthCm", sim.depth_cm)
        return sim
