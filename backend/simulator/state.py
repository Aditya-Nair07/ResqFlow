"""Full flood evacuation simulation state."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from simulator.flood import FloodSimulator
from routing.road_graph import RoadNetwork
from dispatch.assign import run_dispatch_tick
from dispatch.reroute import check_enroute_validity, try_reroute
from routing.router import find_path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_DIR = REPO_ROOT / "scenarios"


def load_scenario(scenario_id: str = "urban_flood_default") -> dict[str, Any]:
    path = SCENARIOS_DIR / f"{scenario_id}.json"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")
    with path.open(encoding="utf-8") as f:
        return json.load(f)


class FloodEvacState:
    """Deterministic urban flood evacuation plant state."""

    def __init__(self, scenario: dict[str, Any]):
        self.scenario_id = scenario["id"]
        self.scenario = scenario
        self.tick = 0
        self.flood = FloodSimulator(
            grid_size=scenario["gridSize"],
            rainfall_per_tick=scenario.get("rainfallPerTick", 0.3),
            drain_rate=scenario.get("drainRate", 0.02),
            depth_spread=scenario.get("depthSpread", 0.1),
            low_points=scenario.get("lowPoints", []),
        )
        self.road = RoadNetwork.from_scenario(scenario)
        self.shelters = [deepcopy(s) for s in scenario["shelters"]]
        for s in self.shelters:
            s.setdefault("occupancy", 0)
            s.setdefault("open", True)
            s.setdefault("reservedCapacity", 0)
        self.groups = [self._init_group(g) for g in scenario["groups"]]
        self.vehicles = [self._init_vehicle(v) for v in scenario["vehicles"]]
        self.depots = deepcopy(scenario.get("depots", []))
        self.traces: list[dict[str, Any]] = []
        self.metrics = {
            "peopleEvacuated": 0,
            "repairs": 0,
            "reroutes": 0,
            "unsafeActuations": 0,
            "strandedGroups": 0,
        }
        self.ranking_method = "hybrid"
        self.closed_loop = True
        self.running = False
        self.last_citizen_report: dict[str, Any] | None = None
        self.citizen_report_count = 0
        self.reports: list[dict[str, Any]] = []
        self.field_updates: list[dict[str, Any]] = []
        self.events: list[dict[str, Any]] = []
        self.event_seq = 0
        self.proposed_plans: dict[str, dict[str, Any]] = {}
        self.plan_version = 0
        self.weather: dict[str, Any] | None = None
        self.reservations: list[dict[str, Any]] = []
        self.difficulty = "normal"
        self.fixture_meta: dict[str, Any] | None = None
        if self.scenario_id.startswith("chennai"):
            from sensing.chennai_fixtures import fixture_meta, seed_chennai_reports_into_plant

            self.fixture_meta = fixture_meta()
            seed_chennai_reports_into_plant(self, limit=6)

    def emit_event(self, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        from sensing.lifecycle import utc_now

        self.event_seq += 1
        event = {
            "seq": self.event_seq,
            "type": event_type,
            "tick": self.tick,
            "at": utc_now(),
            "payload": payload or {},
        }
        self.events.append(event)
        if len(self.events) > 500:
            self.events = self.events[-400:]
        return event

    @staticmethod
    def _init_group(g: dict[str, Any]) -> dict[str, Any]:
        out = deepcopy(g)
        out.setdefault("status", "pending")
        out.setdefault("assignedVehicleId", None)
        out.setdefault("assignedShelterId", None)
        out.setdefault("evacuatedPeople", 0)
        out.setdefault("source", "SIMULATOR")
        out.setdefault("trust", 80)
        out.setdefault("severity", "MEDIUM")
        out.setdefault("confidenceScore", 70)
        out.setdefault("audit", [])
        out.setdefault("createdTick", 0)
        return out

    @staticmethod
    def _init_vehicle(v: dict[str, Any]) -> dict[str, Any]:
        out = deepcopy(v)
        out.setdefault("status", "available")
        out.setdefault("assignedGroupId", None)
        out.setdefault("route", [])
        out.setdefault("routeTickProgress", 0)
        out.setdefault("load", 0)
        out.setdefault("targetShelterId", None)
        out.setdefault("phase", "idle")  # idle | to_pickup | loading | to_shelter | returning
        return out

    def reset(self, scenario: dict[str, Any] | None = None) -> None:
        if scenario:
            self.__init__(scenario)
        else:
            self.__init__(load_scenario(self.scenario_id))

    def advance_flood(self) -> dict[str, Any]:
        info = self.flood.advance()
        self.tick = self.flood.tick
        return info

    def step_simulation(self) -> dict[str, Any]:
        """One tick: flood, move vehicles, dispatch if running."""
        flood_info = self.advance_flood()
        reroute_events = self._move_vehicles()
        dispatch_info = {}
        if self.running:
            dispatch_info = run_dispatch_tick(self)
        return {
            "tick": self.tick,
            "flood": flood_info,
            "reroutes": reroute_events,
            "dispatch": dispatch_info,
            "metrics": dict(self.metrics),
        }

    def _move_vehicles(self) -> list[dict[str, Any]]:
        events = []
        for v in self.vehicles:
            if v["status"] != "busy" or not v.get("route"):
                continue
            valid, reason = check_enroute_validity(self, v)
            if not valid:
                reroute = try_reroute(self, v)
                events.append({
                    "vehicleId": v["id"],
                    "reason": reason,
                    "action": reroute.get("action", "halt"),
                    "detail": reroute.get("reason"),
                })
                self.metrics["reroutes"] += 1
                if reroute.get("action") != "rerouted":
                    v["route"] = []
                    v["status"] = "available"
                    v["phase"] = "idle"
                    gid = v.get("assignedGroupId")
                    if gid:
                        group = next((g for g in self.groups if g["id"] == gid), None)
                        if group and group["status"] == "assigned":
                            group["status"] = "pending"
                            group["assignedVehicleId"] = None
                            group["assignedShelterId"] = None
                continue
            seg_idx = v.get("routeSegmentIndex", 0)
            route = v.get("route") or []
            if not route:
                continue
            seg = route[min(seg_idx, len(route) - 1)]
            v["routeTickProgress"] = v.get("routeTickProgress", 0) + 1
            if v["routeTickProgress"] >= seg.get("ticks", 1):
                seg_idx += 1
                v["routeSegmentIndex"] = seg_idx
                v["routeTickProgress"] = 0
                if seg_idx >= len(route):
                    self._complete_leg(v)
                    v["routeSegmentIndex"] = 0
        return events

    def _complete_leg(self, v: dict[str, Any]) -> None:
        phase = v.get("phase", "idle")
        if phase == "to_pickup":
            v["phase"] = "loading"
            v["routeTickProgress"] = 0
            v["route"] = [{"type": "wait", "ticks": 1}]
        elif phase == "loading":
            gid = v.get("assignedGroupId")
            group = next((g for g in self.groups if g["id"] == gid), None)
            if group:
                take = min(group["people"] - group.get("evacuatedPeople", 0), v["capacity"] - v.get("load", 0))
                v["load"] = v.get("load", 0) + take
                group["evacuatedPeople"] = group.get("evacuatedPeople", 0) + take
            v["phase"] = "to_shelter"
            v["routeTickProgress"] = 0
            sid = v.get("targetShelterId")
            shelter = next((s for s in self.shelters if s["id"] == sid), None)
            if group and shelter:
                pickup = group.get("node", [int(group["x"]), int(group["y"])])
                shelter_node = shelter.get("node", [int(shelter["x"]), int(shelter["y"])])
                path = find_path(
                    self.road, self.flood, pickup, shelter_node,
                    v.get("mode", "road"), v.get("maxDepthCm", 25),
                )
                ticks = path.get("travelTime", 6) if path.get("ok") else 99
                v["route"] = [{"type": "transit", "ticks": ticks}]
                v["activePath"] = path
            else:
                v["route"] = [{"type": "transit", "ticks": 6}]
        elif phase == "to_shelter":
            sid = v.get("targetShelterId")
            shelter = next((s for s in self.shelters if s["id"] == sid), None)
            if shelter:
                shelter["occupancy"] = shelter.get("occupancy", 0) + v.get("load", 0)
                self.metrics["peopleEvacuated"] += v.get("load", 0)
            gid = v.get("assignedGroupId")
            group = next((g for g in self.groups if g["id"] == gid), None)
            if group and group.get("evacuatedPeople", 0) >= group["people"]:
                group["status"] = "evacuated"
            else:
                group["status"] = "pending"
                group["assignedVehicleId"] = None
                group["assignedShelterId"] = None
            v["load"] = 0
            v["assignedGroupId"] = None
            v["targetShelterId"] = None
            v["status"] = "available"
            v["phase"] = "idle"
            v["route"] = []
            v["routeTickProgress"] = 0

    def pending_groups(self) -> list[dict[str, Any]]:
        from sensing.lifecycle import DISPATCHABLE

        return [
            g
            for g in self.groups
            if g["status"] == "pending" or g.get("status") in DISPATCHABLE or g.get("lifecycle") == "PRIORITIZED"
        ]

    def available_vehicles(self) -> list[dict[str, Any]]:
        return [v for v in self.vehicles if v["status"] == "available"]

    def apply_citizen_report(
        self,
        x: int,
        y: int,
        severity: str = "rising",
        note: str = "",
        people: int = 0,
        reporter: str = "resident",
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Apply a software-only citizen waterlogging report (Part A sensing)."""
        from sensing.reports import apply_citizen_sensing

        return apply_citizen_sensing(
            self,
            x=x,
            y=y,
            severity_label=severity,
            note=note,
            people=people,
            reporter=reporter,
            source=kwargs.get("source", "CITIZEN"),
            elderly=kwargs.get("elderly", 0),
            children=kwargs.get("children", 0),
            disabled=kwargs.get("disabled", 0),
            pregnant=kwargs.get("pregnant", 0),
            medical=kwargs.get("medical", False),
            mobility=kwargs.get("mobility", "ambulatory"),
            area=kwargs.get("area", ""),
            landmark=kwargs.get("landmark", ""),
            photo=kwargs.get("photo", False),
            lat=kwargs.get("lat"),
            lng=kwargs.get("lng"),
            depth_cm=kwargs.get("depth_cm"),
        )

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "scenarioId": self.scenario_id,
            "tick": self.tick,
            "flood": self.flood.to_dict(),
            "shelters": self.shelters,
            "groups": self.groups,
            "vehicles": self.vehicles,
            "depots": self.depots,
            "roadEdges": self.scenario.get("roadEdges", []),
            "boatLinks": self.scenario.get("boatLinks", []),
            "roadEdgeStates": self.road.edge_states(self.flood),
            "metrics": self.metrics,
            "rankingMethod": self.ranking_method,
            "closedLoop": self.closed_loop,
            "recentTraces": self.traces[-10:],
            "lastCitizenReport": self.last_citizen_report,
            "reports": self.reports[-50:],
            "fieldUpdates": self.field_updates[-20:],
            "events": self.events[-30:],
            "eventSeq": self.event_seq,
            "planVersion": self.plan_version,
            "weather": self.weather,
            "reservations": self.reservations[-20:],
            "difficulty": getattr(self, "difficulty", "normal"),
            "fixtureMeta": getattr(self, "fixture_meta", None),
            "rainfallPerTick": getattr(self.flood, "rainfall_per_tick", None),
        }
