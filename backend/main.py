from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import LLM_PROVIDER, PORT, llm_configured
from graph import analyze_assignment, build_graph, export_graph_for_viz, get_incident_subgraph, graph_stats, ripple_check
from graph_store import list_saved_traces, load_saved_trace, save_trace_analysis
from llm import generate_text
from local_text import local_briefing, local_report
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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=PORT, reload=True)
