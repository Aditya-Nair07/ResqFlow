"""Extended schemas for ResQFlow-Flood."""

from typing import Any, Literal

from pydantic import BaseModel, Field

# Legacy schemas retained for backward compatibility
from schemas import (  # noqa: F401
    AgentOpinion,
    CandidateBid,
    CandidateCouncil,
    CouncilRequest,
    CouncilResponse,
    GraphAnalyzeRequest,
    GraphEvidenceResponse,
    GraphFullRequest,
    GraphFullResponse,
    IncidentSnapshot,
    ResourceSnapshot,
    SimulationSnapshot,
    TextResponse,
    TraceSnapshot,
    TraceWinner,
)


class ShelterSnapshot(BaseModel):
    id: str
    label: str = ""
    x: float
    y: float
    capacity: int = 0
    occupancy: int = 0
    reservedCapacity: int = 0
    open: bool = True
    node: list[int] | None = None


class EvacuationGroupSnapshot(BaseModel):
    id: str
    label: str = ""
    x: float
    y: float
    people: int = 0
    vulnerability: int = 50
    mobility: str = "ambulatory"
    deadlineTick: int = 999
    status: str = "pending"
    evacuatedPeople: int = 0
    assignedVehicleId: int | str | None = None
    assignedShelterId: str | None = None
    node: list[int] | None = None
    source: str | None = None
    trust: int | None = None
    severity: str | None = None
    confidenceScore: int | None = None
    gapdScore: float | None = None
    gapdBand: int | None = None
    lifecycle: str | None = None
    audit: list[dict[str, Any]] = Field(default_factory=list)
    area: str | None = None
    landmark: str | None = None
    description: str | None = None
    lat: float | None = None
    lng: float | None = None


class FloodVehicleSnapshot(BaseModel):
    id: int | str
    type: str
    mode: Literal["road", "water"] = "road"
    maxDepthCm: float = 25
    capacity: int = 0
    speed: float = 1.0
    fuel: float = 100
    x: float
    y: float
    status: str = "available"
    load: int = 0
    phase: str = "idle"
    assignedGroupId: str | None = None
    targetShelterId: str | None = None


class FloodFrameSnapshot(BaseModel):
    tick: int = 0
    gridSize: int = 25
    depthCm: list[list[float]] = Field(default_factory=list)
    maxDepthCm: float = 0
    floodedCells: int = 0


class FloodEvacSnapshot(BaseModel):
    scenarioId: str = "urban_flood_default"
    tick: int = 0
    flood: FloodFrameSnapshot | dict[str, Any] = Field(default_factory=dict)
    shelters: list[ShelterSnapshot | dict[str, Any]] = Field(default_factory=list)
    groups: list[EvacuationGroupSnapshot | dict[str, Any]] = Field(default_factory=list)
    vehicles: list[FloodVehicleSnapshot | dict[str, Any]] = Field(default_factory=list)
    depots: list[dict[str, Any]] = Field(default_factory=list)
    roadEdgeStates: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    rankingMethod: str = "hybrid"
    closedLoop: bool = True
    recentTraces: list[dict[str, Any]] = Field(default_factory=list)
    lastCitizenReport: dict[str, Any] | None = None
    roadEdges: list[dict[str, Any]] = Field(default_factory=list)
    boatLinks: list[dict[str, Any]] = Field(default_factory=list)
    reports: list[dict[str, Any]] = Field(default_factory=list)
    fieldUpdates: list[dict[str, Any]] = Field(default_factory=list)
    events: list[dict[str, Any]] = Field(default_factory=list)
    eventSeq: int = 0
    planVersion: int = 0
    weather: dict[str, Any] | None = None
    reservations: list[dict[str, Any]] = Field(default_factory=list)
    difficulty: str = "normal"
    fixtureMeta: dict[str, Any] | None = None
    rainfallPerTick: float | None = None


class ScenarioListResponse(BaseModel):
    scenarios: list[dict[str, str]]


class SimulateStepRequest(BaseModel):
    scenarioId: str = "urban_flood_default"
    steps: int = 1
    running: bool | None = None
    rankingMethod: str | None = None
    closedLoop: bool | None = None
    difficulty: Literal["normal", "heavy", "crisis"] | None = None


class DifficultyRequest(BaseModel):
    scenarioId: str = "chennai_2015_review"
    difficulty: Literal["normal", "heavy", "crisis"] = "normal"


class ResetRequest(BaseModel):
    scenarioId: str = "chennai_2015_review"
    difficulty: Literal["normal", "heavy", "crisis"] = "normal"
    seedFixtures: bool | None = None


class SimulateStepResponse(BaseModel):
    snapshot: FloodEvacSnapshot
    stepsRun: int = 1


class RoutePlanRequest(BaseModel):
    snapshot: FloodEvacSnapshot
    vehicleId: int | str
    groupId: str
    shelterId: str


class RoutePlanResponse(BaseModel):
    pickup: dict[str, Any]
    shelter: dict[str, Any]
    routeRisk: float = 0
    verification: dict[str, Any] = Field(default_factory=dict)


class CitizenReportRequest(BaseModel):
    scenarioId: str = "urban_flood_default"
    x: int = Field(ge=0, le=40)
    y: int = Field(ge=0, le=40)
    severity: Literal["shallow", "rising", "knee_deep", "impassable"] = "rising"
    note: str = ""
    people: int = Field(default=0, ge=0, le=200)
    reporter: str = "resident"
    source: str = "CITIZEN"
    elderly: int = Field(default=0, ge=0)
    children: int = Field(default=0, ge=0)
    disabled: int = Field(default=0, ge=0)
    pregnant: int = Field(default=0, ge=0)
    medical: bool = False
    mobility: str = "ambulatory"
    area: str = ""
    landmark: str = ""
    photo: bool = False
    lat: float | None = None
    lng: float | None = None
    depthCm: float | None = None


class CitizenReportResponse(BaseModel):
    report: dict[str, Any]
    snapshot: FloodEvacSnapshot


class OperatorReportRequest(BaseModel):
    scenarioId: str = "urban_flood_default"
    groupId: str | None = None
    reportId: str | None = None
    actor: str = "operator"
    source: Literal["OPERATOR", "FIELD_TEAM", "WARD_VOLUNTEER"] = "OPERATOR"
    observedDepthCm: float | None = None
    roadStatus: Literal["OPEN", "SLOW", "BLOCKED", "UNKNOWN"] | None = None
    roadEdgeId: str | None = None
    x: float | None = None
    y: float | None = None
    peopleFound: int | None = None
    peopleBoarded: int | None = None
    vehicleId: int | str | None = None
    vehicleStatus: str | None = None
    shelterId: str | None = None
    shelterClosed: bool | None = None
    shelterFull: bool | None = None
    note: str = ""
    reinforcement: bool = False


class FieldUpdateRequest(OperatorReportRequest):
    """Alias schema for POST /flood/field-updates."""


class PlanCompareRequest(BaseModel):
    scenarioId: str = "urban_flood_default"
    rankingMethod: str | None = None


class PlanApproveRequest(BaseModel):
    scenarioId: str = "urban_flood_default"
    planId: str
    planVersion: int | None = None
    tick: int | None = None
    actor: str = "operator"
    override: bool = False
    overrideReason: str = ""


class IncidentActionRequest(BaseModel):
    scenarioId: str = "urban_flood_default"
    actor: str = "operator"
    accept: bool = True


class WeatherRequest(BaseModel):
    scenarioId: str = "urban_flood_default"
    area: str = "Chennai"
    lat: float = 13.0827
    lon: float = 80.2707
    applyNudge: bool = True


class ReplanRequest(BaseModel):
    scenarioId: str = "urban_flood_default"
    rankingMethod: str | None = None
    closedLoop: bool | None = None
