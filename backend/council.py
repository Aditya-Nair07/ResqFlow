"""Multi-agent council — graph-grounded review of allocation candidates."""

from __future__ import annotations

import asyncio
import json
import math
from typing import Any

from graph import analyze_assignment
from llm import openai_compatible_chat
from config import AICREDITS_BASE_URL, AICREDITS_MODEL, LLM_PROVIDER, llm_configured
from schemas import CandidateBid, CouncilResponse, CandidateCouncil, AgentOpinion, SimulationSnapshot

AGENTS = ("medical", "logistics", "route")


def _dist(ax: float, ay: float, bx: float, by: float) -> float:
    return math.hypot(ax - bx, ay - by)


def _nearest_base(snapshot: SimulationSnapshot, x: float, y: float) -> float:
    best = float("inf")
    for base in snapshot.bases:
        best = min(best, _dist(x, y, base["x"], base["y"]))
    return best


def _heuristic_medical(resource: dict, incident: dict, subgraph: dict) -> AgentOpinion:
    caps = resource.get("capabilities") or []
    need = incident.get("need", "")
    capability = 100 if need in caps else (62 if need else 18)
    people = incident.get("people", 1)
    capacity = resource.get("capacity", 1)
    urgency = incident.get("urgency", 50)
    delta = 0
    concerns: list[str] = []

    if need in caps:
        delta += 8
    elif capability < 50:
        delta -= 12
        concerns.append("Weak capability match for incident need.")
    if urgency >= 88 and need in caps:
        delta += 4
    if people > capacity:
        delta -= 10
        concerns.append(f"Capacity {capacity} below {people} people affected.")

    if not concerns:
        concerns.append("Medical triage: acceptable capability and urgency alignment.")

    evidence = [n["id"] for n in subgraph.get("nodes", []) if n.get("kind") == "Incident"][:2]
    return AgentOpinion(
        agent="medical",
        score_delta=max(-20, min(20, delta)),
        confidence=0.85 if need in caps else 0.55,
        concerns=concerns[:2],
        evidence_nodes=evidence,
    )


def _heuristic_logistics(resource: dict, incident: dict, snapshot: SimulationSnapshot, subgraph: dict) -> AgentOpinion:
    fuel = resource.get("fuel", 50)
    dist = _dist(resource.get("x", 0), resource.get("y", 0), incident.get("x", 0), incident.get("y", 0))
    fuel_cost = max(8, round(dist * 0.55))
    base_dist = _nearest_base(snapshot, resource.get("x", 0), resource.get("y", 0))
    delta = 0
    concerns: list[str] = []

    if fuel < 30:
        delta -= 10
        concerns.append("Low fuel limits further deployments.")
    elif fuel - fuel_cost < 15:
        delta -= 6
        concerns.append("Tight fuel margin after this route.")
    if base_dist <= 18:
        delta += 5
    if resource.get("status") != "available":
        delta -= 15

    pending_same = sum(
        1
        for i in snapshot.incidents
        if i.status == "pending" and str(i.id) != str(incident.get("id"))
        and i.need in (resource.get("capabilities") or [])
    )
    if pending_same:
        delta -= 4
        concerns.append(f"{pending_same} other pending incident(s) may lose nearest capable unit.")

    if not concerns:
        concerns.append("Logistics: fuel and depot proximity acceptable.")

    evidence = [n["id"] for n in subgraph.get("nodes", []) if n.get("kind") == "Base"][:1]
    return AgentOpinion(
        agent="logistics",
        score_delta=max(-20, min(20, delta)),
        confidence=0.8,
        concerns=concerns[:2],
        evidence_nodes=evidence,
    )


def _heuristic_route(resource: dict, incident: dict, subgraph: dict, route_risk: float) -> AgentOpinion:
    delta = 0
    concerns: list[str] = []

    if route_risk >= 65:
        delta -= 12
        concerns.append(f"Route exposure elevated (risk {round(route_risk)}).")
    elif route_risk >= 50:
        delta -= 5
    else:
        delta += 4

    risk_nodes = [n for n in subgraph.get("nodes", []) if n.get("kind") == "RiskZone"]
    if risk_nodes:
        concerns.append(f"Path near {risk_nodes[0].get('label', 'risk zone')}.")

    if len(concerns) < 2:
        concerns.append("Route safety: within acceptable exposure band.")

    evidence = [n["id"] for n in risk_nodes[:2]]
    return AgentOpinion(
        agent="route",
        score_delta=max(-20, min(20, delta)),
        confidence=0.82 if route_risk < 60 else 0.6,
        concerns=concerns[:2],
        evidence_nodes=evidence,
    )


def review_candidate_heuristic(
    snapshot: SimulationSnapshot,
    incident: dict,
    resource: dict,
    bid: CandidateBid,
    subgraph: dict,
) -> list[AgentOpinion]:
    route_risk = bid.score.get("routeRisk", 50) if isinstance(bid.score, dict) else 50
    return [
        _heuristic_medical(resource, incident, subgraph),
        _heuristic_logistics(resource, incident, snapshot, subgraph),
        _heuristic_route(resource, incident, subgraph, route_risk),
    ]


async def _llm_agent_review(
    agent_name: str,
    snapshot: SimulationSnapshot,
    incident: dict,
    candidates: list[dict],
    subgraph: dict,
) -> list[dict]:
    prompts = {
        "medical": "Medical Triage Agent: judge urgency, capability match, people vs capacity.",
        "logistics": "Logistics & Fuel Agent: judge fuel drain, depot distance, competing assignments.",
        "route": "Route Safety Agent: judge risk zones, route exposure, blocked paths.",
    }
    system = (
        f"You are the {prompts[agent_name]} Return ONLY valid JSON array, one object per candidate resource_id:\n"
        '[{"resource_id": "2", "score_delta": -5, "confidence": 0.8, "concerns": ["..."], "evidence_nodes": ["incident:1"]}]\n'
        "score_delta integer from -15 to +15. Max 2 short concerns per candidate."
    )
    payload = {
        "incident": incident,
        "candidates": candidates,
        "subgraph_summary": subgraph.get("summary", ""),
        "subgraph_nodes": subgraph.get("nodes", [])[:12],
    }
    prompt = f"{system}\n\nContext JSON:\n{json.dumps(payload, indent=2)}"
    text = await openai_compatible_chat(prompt)
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        return json.loads(text[start:end])
    return []


async def run_llm_council(
    snapshot: SimulationSnapshot,
    incident_id: str | int,
    candidates: list[CandidateBid],
    subgraph: dict,
) -> dict[str, list[AgentOpinion]] | None:
    if not llm_configured() or LLM_PROVIDER not in ("openai", "aicredits", "openrouter"):
        return None

    incident = next((i for i in snapshot.incidents if str(i.id) == str(incident_id)), None)
    if not incident:
        return None

    cand_payload = []
    for bid in candidates[:3]:
        res = next((r for r in snapshot.resources if str(r.id) == str(bid.resource_id)), None)
        if not res:
            continue
        cand_payload.append(
            {
                "resource_id": str(bid.resource_id),
                "type": res.type,
                "fuel": res.fuel,
                "capabilities": res.capabilities,
                "base_score": bid.score.get("total", 0) if isinstance(bid.score, dict) else 0,
            }
        )

    inc_dict = incident.model_dump()
    opinions_by_resource: dict[str, list[AgentOpinion]] = {}

    async def run_agent(name: str):
        try:
            rows = await _llm_agent_review(name, snapshot, inc_dict, cand_payload, subgraph)
            for row in rows:
                rid = str(row.get("resource_id", ""))
                opinions_by_resource.setdefault(rid, []).append(
                    AgentOpinion(
                        agent=name,
                        score_delta=max(-15, min(15, int(row.get("score_delta", 0)))),
                        confidence=float(row.get("confidence", 0.7)),
                        concerns=(row.get("concerns") or [])[:2],
                        evidence_nodes=(row.get("evidence_nodes") or [])[:3],
                    )
                )
        except Exception:
            pass

    await asyncio.gather(*[run_agent(a) for a in AGENTS])
    return opinions_by_resource if opinions_by_resource else None


async def run_council(
    snapshot: SimulationSnapshot,
    incident_id: str | int,
    candidates: list[CandidateBid],
) -> CouncilResponse:
    incident = next((i for i in snapshot.incidents if str(i.id) == str(incident_id)), None)
    if not incident:
        return CouncilResponse(available=False, source="none", incident_id=incident_id, candidates=[])

    top_rid = candidates[0].resource_id if candidates else None
    analysis = analyze_assignment(snapshot, incident_id, resource_id=top_rid, hops=2)
    subgraph = analysis.get("subgraph", {})

    inc_dict = incident.model_dump()
    result_candidates: list[CandidateCouncil] = []
    source = "heuristic"

    llm_opinions: dict[str, list[AgentOpinion]] | None = None
    if llm_configured():
        try:
            llm_opinions = await run_llm_council(snapshot, incident_id, candidates, subgraph)
            if llm_opinions:
                source = "llm"
        except Exception:
            llm_opinions = None

    for bid in candidates[:3]:
        res = next((r for r in snapshot.resources if str(r.id) == str(bid.resource_id)), None)
        if not res:
            continue
        res_dict = res.model_dump()

        if llm_opinions and str(bid.resource_id) in llm_opinions:
            opinions = list(llm_opinions[str(bid.resource_id)])
            full = review_candidate_heuristic(snapshot, inc_dict, res_dict, bid, subgraph)
            for o in full:
                if not any(x.agent == o.agent for x in opinions):
                    opinions.append(o)
        else:
            opinions = review_candidate_heuristic(snapshot, inc_dict, res_dict, bid, subgraph)

        merged = sum(o.score_delta for o in opinions)
        merged = max(-25, min(25, merged))
        base = bid.score.get("total", 0) if isinstance(bid.score, dict) else 0

        result_candidates.append(
            CandidateCouncil(
                resource_id=bid.resource_id,
                resource_type=res.type,
                opinions=opinions,
                merged_delta=merged,
                adjusted_total=clamp_score(base + merged),
            )
        )

    narrative = _build_narrative(result_candidates, source)
    return CouncilResponse(
        available=True,
        source=source,
        incident_id=incident_id,
        candidates=result_candidates,
        narrative=narrative,
        subgraph_summary=subgraph.get("summary", ""),
    )


def clamp_score(value: int) -> int:
    return max(0, min(100, value))


def _build_narrative(candidates: list[CandidateCouncil], source: str) -> str:
    if not candidates:
        return "No candidates reviewed."
    best = max(candidates, key=lambda c: c.adjusted_total)
    base = best.adjusted_total - best.merged_delta
    mode = "AI specialists" if source == "llm" else "rule-based specialists"
    return (
        f"{mode} reviewed {len(candidates)} top candidates on the graph. "
        f"Recommended {best.resource_type} R{best.resource_id}: "
        f"base score {base} → {best.adjusted_total} after council ({best.merged_delta:+d})."
    )
