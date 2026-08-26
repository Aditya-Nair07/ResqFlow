from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from config import LLM_PROVIDER, PORT, llm_configured
from graph import analyze_assignment, build_graph, export_graph_for_viz, get_incident_subgraph, graph_stats, ripple_check
from graph_store import list_saved_traces, load_saved_trace, save_trace_analysis
from llm import generate_text
from local_text import local_briefing, local_report
from flood_schemas import (
    CitizenReportRequest,
    CitizenReportResponse,
    DifficultyRequest,
    FieldUpdateRequest,
    FloodEvacSnapshot,
    IncidentActionRequest,
    OperatorReportRequest,
    PlanApproveRequest,
    PlanCompareRequest,
    ReplanRequest,
    ResetRequest,
    RoutePlanRequest,
    RoutePlanResponse,
    ScenarioListResponse,
    SimulateStepRequest,
    SimulateStepResponse,
    WeatherRequest,
)
from flood_service import get_or_create_session, list_scenarios, reset_session
from flood_graph import analyze_flood_assignment
from dispatch.verify import verify_evacuation_plan
from dispatch.scoring import rank_candidate
from dispatch.plans import compare_plans
from dispatch.approve import approve_plan, store_compared_plans
from routing.router import find_path, route_risk
from sensing.reports import apply_operator_sensing, prioritize_incident, verify_incident
from sensing.weather import fetch_open_meteo, weather_to_rainfall_nudge
from sensing.chennai_fixtures import apply_difficulty, fixture_meta, load_citizen_reports, load_shelter_summary
from council import run_council
from schemas import (
    CouncilRequest,
    CouncilResponse,
    GraphAnalyzeRequest,
    GraphEvidenceResponse,
    GraphFullRequest,
    GraphFullResponse,
    SimulationSnapshot,
    TextResponse,
)

app = FastAPI(title="ResQFlow API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "resqflow-api",
        "llm_configured": llm_configured(),
        "provider": LLM_PROVIDER if llm_configured() else None,
        "graph": "networkx",
        "agents": "council",
        "mode": "flood-evacuation",
    }


@app.post("/briefing", response_model=TextResponse)
async def briefing(snapshot: SimulationSnapshot):
    if not llm_configured():
        return TextResponse(text=local_briefing(snapshot), source="local")
    try:
        text = await generate_text("briefing", snapshot)
        return TextResponse(text=text, source="llm", provider=LLM_PROVIDER)
    except Exception:
        return TextResponse(text=local_briefing(snapshot), source="local")


@app.post("/report", response_model=TextResponse)
async def report(snapshot: SimulationSnapshot):
    if not llm_configured():
        return TextResponse(text=local_report(snapshot), source="local")
    try:
        text = await generate_text("report", snapshot)
        return TextResponse(text=text, source="llm", provider=LLM_PROVIDER)
    except Exception:
        return TextResponse(text=local_report(snapshot), source="local")


@app.post("/graph/evidence", response_model=GraphEvidenceResponse)
def graph_evidence(body: GraphAnalyzeRequest):
    result = analyze_assignment(
        body.snapshot,
        body.incidentId,
        resource_id=body.resourceId,
        hops=body.hops,
    )
    saved_to = None
    if body.persist and body.traceId:
        saved_to = save_trace_analysis(
            body.traceId,
            {
                "trace_id": body.traceId,
                "incident_id": body.incidentId,
                "resource_id": body.resourceId,
                "analysis": result,
            },
        )
    return GraphEvidenceResponse(**result, saved_to=saved_to)


@app.post("/graph/subgraph")
def graph_subgraph(body: GraphAnalyzeRequest):
    g = build_graph(body.snapshot)
    return {
        "stats": graph_stats(g),
        "subgraph": get_incident_subgraph(g, body.incidentId, hops=body.hops),
    }


@app.post("/graph/ripple")
def graph_ripple(body: GraphAnalyzeRequest):
    if body.resourceId is None:
        return {"error": "resourceId required"}
    g = build_graph(body.snapshot)
    return ripple_check(g, body.snapshot, body.resourceId, body.incidentId)


@app.post("/graph/full", response_model=GraphFullResponse)
def graph_full(body: GraphFullRequest):
    return export_graph_for_viz(
        body.snapshot,
        incident_id=body.incidentId,
        resource_id=body.resourceId,
        hops=body.hops,
    )


@app.get("/graph/traces")
def graph_traces(limit: int = 20):
    return {"traces": list_saved_traces(limit=limit)}


@app.post("/agents/council", response_model=CouncilResponse)
async def agents_council(body: CouncilRequest):
    return await run_council(body.snapshot, body.incident_id, body.candidates)


@app.get("/graph/traces/{trace_id}")
def graph_trace_detail(trace_id: str):
    record = load_saved_trace(trace_id)
    if not record:
        return {"error": "trace not found"}
    return record


# --- ResQFlow-Flood endpoints ---


@app.get("/flood/scenarios", response_model=ScenarioListResponse)
def flood_scenarios():
    return ScenarioListResponse(scenarios=list_scenarios())


@app.post("/flood/reset")
def flood_reset(
    scenarioId: str = "chennai_2015_review",
    difficulty: str = "normal",
    seedFixtures: bool | None = None,
):
    state = reset_session(scenarioId, difficulty=difficulty, seed_fixtures=seedFixtures)
    state.running = False
    return {"snapshot": state.to_snapshot()}


@app.post("/flood/reset/body")
def flood_reset_body(body: ResetRequest):
    return flood_reset(body.scenarioId, body.difficulty, body.seedFixtures)


@app.post("/flood/difficulty")
def flood_difficulty(body: DifficultyRequest):
    state = get_or_create_session(body.scenarioId)
    info = apply_difficulty(state, body.difficulty)
    return {"difficulty": info, "snapshot": state.to_snapshot()}


@app.get("/flood/chennai/fixtures")
def flood_chennai_fixtures():
    return {
        "meta": fixture_meta(),
        "shelters": load_shelter_summary(),
        "reports": load_citizen_reports(),
    }


@app.get("/flood/snapshot")
def flood_snapshot(scenarioId: str = "chennai_2015_review"):
    state = get_or_create_session(scenarioId)
    return state.to_snapshot()


@app.post("/flood/simulate/step", response_model=SimulateStepResponse)
def flood_simulate_step(body: SimulateStepRequest):
    state = get_or_create_session(body.scenarioId)
    if body.running is not None:
        state.running = body.running
    if body.rankingMethod:
        state.ranking_method = body.rankingMethod
    if body.closedLoop is not None:
        state.closed_loop = body.closedLoop
    if body.difficulty:
        apply_difficulty(state, body.difficulty)
    steps = max(1, min(body.steps, 50))
    for _ in range(steps):
        state.step_simulation()
    snap = state.to_snapshot()
    return SimulateStepResponse(snapshot=FloodEvacSnapshot(**snap), stepsRun=steps)


@app.post("/flood/route/plan", response_model=RoutePlanResponse)
def flood_route_plan(body: RoutePlanRequest):
    snap = body.snapshot.model_dump() if hasattr(body.snapshot, "model_dump") else dict(body.snapshot)
    from simulator.state import FloodEvacState
    from simulator.state import load_scenario

    state = FloodEvacState(load_scenario(snap.get("scenarioId", "urban_flood_default")))
    state.tick = snap.get("tick", 0)
    state.flood.tick = state.tick
    state.flood.depth_cm = snap.get("flood", {}).get("depthCm", state.flood.depth_cm)
    state.groups = snap.get("groups", state.groups)
    state.vehicles = snap.get("vehicles", state.vehicles)
    state.shelters = snap.get("shelters", state.shelters)

    vehicle = next(v for v in state.vehicles if v["id"] == body.vehicleId)
    group = next(g for g in state.groups if g["id"] == body.groupId)
    shelter = next(s for s in state.shelters if s["id"] == body.shelterId)
    pickup_node = group.get("node", [int(group["x"]), int(group["y"])])
    shelter_node = shelter.get("node", [int(shelter["x"]), int(shelter["y"])])
    vnode = state.road.nearest_node(vehicle["x"], vehicle["y"]) or pickup_node
    vn = [int(vnode.split(",")[0]), int(vnode.split(",")[1])]

    path_pickup = find_path(
        state.road, state.flood, vn, pickup_node,
        vehicle.get("mode", "road"), vehicle.get("maxDepthCm", 25),
    )
    eta = path_pickup.get("etaTick", state.tick + 10) if path_pickup.get("ok") else state.tick + 99
    path_shelter = find_path(
        state.road, state.flood, pickup_node, shelter_node,
        vehicle.get("mode", "road"), vehicle.get("maxDepthCm", 25),
        arrival_tick=eta,
    )
    verification = verify_evacuation_plan(state, vehicle, group, shelter, path_pickup, path_shelter)
    risk = route_risk(path_pickup, state.road, state.flood) + route_risk(path_shelter, state.road, state.flood)
    return RoutePlanResponse(
        pickup=path_pickup,
        shelter=path_shelter,
        routeRisk=round(risk, 2),
        verification=verification,
    )


@app.post("/flood/graph/evidence")
def flood_graph_evidence(scenarioId: str = "urban_flood_default", groupId: str = "", vehicleId: str | None = None):
    state = get_or_create_session(scenarioId)
    snap = state.to_snapshot()
    return analyze_flood_assignment(snap, groupId, vehicleId)


@app.post("/flood/report", response_model=CitizenReportResponse)
def flood_citizen_report(body: CitizenReportRequest):
    """Software sensor: citizen waterlogging report updates flood plant state."""
    state = get_or_create_session(body.scenarioId)
    report = state.apply_citizen_report(
        x=body.x,
        y=body.y,
        severity=body.severity,
        note=body.note,
        people=body.people,
        reporter=body.reporter,
        source=body.source,
        elderly=body.elderly,
        children=body.children,
        disabled=body.disabled,
        pregnant=body.pregnant,
        medical=body.medical,
        mobility=body.mobility,
        area=body.area,
        landmark=body.landmark,
        photo=body.photo,
        lat=body.lat,
        lng=body.lng,
        depth_cm=body.depthCm,
    )
    snap = state.to_snapshot()
    return CitizenReportResponse(report=report, snapshot=FloodEvacSnapshot(**snap))


@app.post("/flood/reports/citizen", response_model=CitizenReportResponse)
def flood_reports_citizen(body: CitizenReportRequest):
    return flood_citizen_report(body)


@app.post("/flood/reports/operator")
def flood_reports_operator(body: OperatorReportRequest):
    state = get_or_create_session(body.scenarioId)
    update = apply_operator_sensing(
        state,
        group_id=body.groupId,
        report_id=body.reportId,
        actor=body.actor,
        source=body.source,
        observed_depth_cm=body.observedDepthCm,
        road_status=body.roadStatus,
        road_edge_id=body.roadEdgeId,
        x=body.x,
        y=body.y,
        people_found=body.peopleFound,
        people_boarded=body.peopleBoarded,
        vehicle_id=body.vehicleId,
        vehicle_status=body.vehicleStatus,
        shelter_id=body.shelterId,
        shelter_closed=body.shelterClosed,
        shelter_full=body.shelterFull,
        note=body.note,
        reinforcement=body.reinforcement,
    )
    return {"update": update, "snapshot": state.to_snapshot()}


@app.post("/flood/field-updates")
def flood_field_updates(body: FieldUpdateRequest):
    return flood_reports_operator(body)


@app.get("/flood/incidents")
def flood_incidents(scenarioId: str = "urban_flood_default"):
    state = get_or_create_session(scenarioId)
    return {
        "tick": state.tick,
        "incidents": state.groups,
        "reports": state.reports,
        "events": state.events[-50:],
    }


@app.post("/flood/incidents/{incident_id}/verify")
def flood_incident_verify(incident_id: str, body: IncidentActionRequest):
    state = get_or_create_session(body.scenarioId)
    try:
        group = verify_incident(state, incident_id, actor=body.actor, accept=body.accept)
    except KeyError:
        raise HTTPException(status_code=404, detail="incident not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"incident": group, "snapshot": state.to_snapshot()}


@app.post("/flood/incidents/{incident_id}/prioritize")
def flood_incident_prioritize(incident_id: str, body: IncidentActionRequest):
    state = get_or_create_session(body.scenarioId)
    try:
        group = prioritize_incident(state, incident_id, actor=body.actor)
    except KeyError:
        raise HTTPException(status_code=404, detail="incident not found") from None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return {"incident": group, "snapshot": state.to_snapshot()}


@app.post("/flood/plans/compare")
def flood_plans_compare(body: PlanCompareRequest):
    state = get_or_create_session(body.scenarioId)
    if body.rankingMethod:
        state.ranking_method = body.rankingMethod
    result = compare_plans(state, ranking_method=body.rankingMethod)
    return store_compared_plans(state, result)


@app.post("/flood/plans/{plan_id}/approve")
def flood_plans_approve(plan_id: str, body: PlanApproveRequest):
    state = get_or_create_session(body.scenarioId)
    result = approve_plan(
        state,
        plan_id,
        plan_version=body.planVersion,
        tick=body.tick,
        actor=body.actor,
        override=body.override,
        override_reason=body.overrideReason,
    )
    if not result.get("ok") and result.get("code") in ("PLAN_NOT_FOUND", "STALE_PLAN", "STALE_TICK"):
        raise HTTPException(status_code=409, detail=result)
    return result


@app.post("/flood/replan")
def flood_replan(body: ReplanRequest):
    state = get_or_create_session(body.scenarioId)
    if body.rankingMethod:
        state.ranking_method = body.rankingMethod
    if body.closedLoop is not None:
        state.closed_loop = body.closedLoop
    for g in state.groups:
        if g.get("status") == "REPLAN_REQUIRED":
            g["status"] = "pending"
            g["lifecycle"] = "PRIORITIZED"
    state.running = True
    info = state.step_simulation()
    state.emit_event("replan_required", {"dispatch": info.get("dispatch")})
    return {"dispatch": info, "snapshot": state.to_snapshot()}


@app.post("/flood/weather")
def flood_weather(body: WeatherRequest):
    weather = fetch_open_meteo(lat=body.lat, lon=body.lon, area=body.area)
    state = get_or_create_session(body.scenarioId)
    state.weather = weather
    if body.applyNudge:
        nudge = weather_to_rainfall_nudge(weather)
        state.flood.rainfall_per_tick = max(state.flood.rainfall_per_tick, state.scenario.get("rainfallPerTick", 0.3) + nudge)
    state.emit_event("weather_updated", weather)
    return {"weather": weather, "snapshot": state.to_snapshot()}


@app.get("/flood/traces")
def flood_traces(scenarioId: str = "urban_flood_default"):
    state = get_or_create_session(scenarioId)
    return {"traces": state.traces, "saved": list_saved_traces()}


@app.get("/flood/events")
def flood_events(scenarioId: str = "urban_flood_default", after: int = 0):
    state = get_or_create_session(scenarioId)
    events = [e for e in state.events if e.get("seq", 0) > after]
    return {"events": events, "eventSeq": state.event_seq, "tick": state.tick}


@app.get("/flood/events/stream")
async def flood_events_stream(scenarioId: str = "urban_flood_default"):
    """SSE stream of plant events; clients should reconnect automatically."""
    import asyncio
    import json

    async def gen():
        last = 0
        while True:
            state = get_or_create_session(scenarioId)
            fresh = [e for e in state.events if e.get("seq", 0) > last]
            for event in fresh:
                last = event["seq"]
                yield f"data: {json.dumps(event)}\n\n"
            # heartbeat for reconnect clients
            yield f": ping {state.tick}\n\n"
            await asyncio.sleep(1.0)

    return StreamingResponse(gen(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
