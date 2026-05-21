from typing import Any, Literal

from pydantic import BaseModel, Field


class ResourceSnapshot(BaseModel):
    id: int | str
    type: str
    x: float
    y: float
    fuel: float
    status: str
    capabilities: list[str] = Field(default_factory=list)
    capacity: int = 0
    assignedIncidentId: int | str | None = None
    completed: int = 0


class IncidentSnapshot(BaseModel):
    id: int | str
    type: str
    need: str
    urgency: int
    people: int
    x: float
    y: float
    status: str
    assignedResourceId: int | str | None = None
    sourceText: str = ""


class TraceWinner(BaseModel):
    resource: dict[str, Any]
    score: dict[str, Any]


class TraceSnapshot(BaseModel):
    traceId: str
    time: str = ""
    strategy: str = ""
    outcome: str = ""
    playbookHint: str = ""
    incident: dict[str, Any] | None = None
    winner: TraceWinner | None = None
    topRejected: list[dict[str, Any]] = Field(default_factory=list)
    checks: list[dict[str, Any]] = Field(default_factory=list)


class SimulationSnapshot(BaseModel):
    strategy: str
    resolved: int = 0
    repairCount: int = 0
    decisions: int = 0
    totalScore: float = 0
    bases: list[dict[str, Any]] = Field(default_factory=list)
    riskZones: list[dict[str, Any]] = Field(default_factory=list)
    resources: list[ResourceSnapshot] = Field(default_factory=list)
    incidents: list[IncidentSnapshot] = Field(default_factory=list)
    latestTrace: TraceSnapshot | None = None
    recentTraces: list[TraceSnapshot] = Field(default_factory=list)


class TextResponse(BaseModel):
    text: str
    source: Literal["llm", "local"] = "local"
    provider: str | None = None


class GraphAnalyzeRequest(BaseModel):
    snapshot: SimulationSnapshot
    incidentId: str | int
    resourceId: str | int | None = None
    traceId: str | None = None
    hops: int = 2
    persist: bool = True


class GraphEvidenceResponse(BaseModel):
    available: bool = True
    stats: dict[str, Any] = Field(default_factory=dict)
    subgraph: dict[str, Any] = Field(default_factory=dict)
    ripple: dict[str, Any] | None = None
    evidence: dict[str, Any] | None = None
    saved_to: str | None = None


class GraphFullRequest(BaseModel):
    snapshot: SimulationSnapshot
    incidentId: str | int | None = None
    resourceId: str | int | None = None
    hops: int = 2


class GraphFullResponse(BaseModel):
    nodes: list[dict[str, Any]] = Field(default_factory=list)
    edges: list[dict[str, Any]] = Field(default_factory=list)
    stats: dict[str, Any] = Field(default_factory=dict)
    focus: dict[str, Any] = Field(default_factory=dict)


class CandidateBid(BaseModel):
    resource_id: str | int
    resource_type: str = ""
    score: dict[str, Any] = Field(default_factory=dict)


class AgentOpinion(BaseModel):
    agent: str
    score_delta: int = 0
    confidence: float = 0.7
    concerns: list[str] = Field(default_factory=list)
    evidence_nodes: list[str] = Field(default_factory=list)


class CandidateCouncil(BaseModel):
    resource_id: str | int
    resource_type: str = ""
    opinions: list[AgentOpinion] = Field(default_factory=list)
    merged_delta: int = 0
    adjusted_total: int = 0


class CouncilRequest(BaseModel):
    snapshot: SimulationSnapshot
    incident_id: str | int
    candidates: list[CandidateBid] = Field(default_factory=list)


class CouncilResponse(BaseModel):
    available: bool = True
    source: Literal["llm", "heuristic", "none"] = "heuristic"
    incident_id: str | int | None = None
    candidates: list[CandidateCouncil] = Field(default_factory=list)
    narrative: str = ""
    subgraph_summary: str = ""
