from collections import Counter

from schemas import SimulationSnapshot


def _count_needs(snapshot: SimulationSnapshot) -> str:
    open_incidents = [i for i in snapshot.incidents if i.status != "resolved"]
    counts = Counter(i.need for i in open_incidents)
    if not counts:
        return "none"
    return ", ".join(f"{need} ({n})" for need, n in counts.most_common(3))


def local_briefing(snapshot: SimulationSnapshot) -> str:
    open_incidents = [i for i in snapshot.incidents if i.status != "resolved"]
    critical = [i for i in open_incidents if i.urgency >= 85]
    free = [r for r in snapshot.resources if r.status == "available"]
    latest = snapshot.latestTrace
    lines = [
        "Situation briefing (local):",
        f"- Open incidents: {len(open_incidents)}; critical: {len(critical)}; available resources: {len(free)}.",
        f"- Dominant needs: {_count_needs(snapshot)}.",
        f"- Active strategy: {snapshot.strategy}.",
    ]
    if latest and latest.winner:
        w = latest.winner
        rid = w.resource.get("id")
        rtype = w.resource.get("type")
        score = w.score.get("total")
        inc = latest.incident or {}
        lines.append(
            f"- Latest: {latest.traceId} assigned {rtype} R{rid} to {inc.get('type', 'incident')} (score {score})."
        )
    else:
        lines.append("- Latest: no committed assignment yet.")
    if latest and latest.playbookHint:
        lines.append(f"- Context: {latest.playbookHint}")
    lines.append("- Scoring weighs urgency, distance, capability, fuel margin, and route risk before commit.")
    return "\n".join(lines)


def local_report(snapshot: SimulationSnapshot) -> str:
    open_incidents = [i for i in snapshot.incidents if i.status != "resolved"]
    assigned = [i for i in snapshot.incidents if i.status == "assigned"]
    pending = [i for i in snapshot.incidents if i.status == "pending"]
    busy = [r for r in snapshot.resources if r.status != "available"]
    utilization = round(len(busy) / max(len(snapshot.resources), 1) * 100)
    avg_score = round(snapshot.totalScore / snapshot.decisions) if snapshot.decisions else 0
    trace_lines = []
    for trace in snapshot.recentTraces[:4]:
        winner = trace.winner
        if winner:
            detail = f"selected R{winner.resource.get('id')}"
        else:
            detail = "no safe assignment"
        trace_lines.append(f"  - {trace.traceId}: {(trace.incident or {}).get('type', 'incident')}, {detail}")
    if not trace_lines:
        trace_lines.append("  - No traces captured yet.")
    return "\n".join(
        [
            "Incident report (local):",
            f"- Resolved incidents: {snapshot.resolved}.",
            f"- Active assignments: {len(assigned)}.",
            f"- Pending incidents: {len(pending)}.",
            f"- Resource utilization: {utilization}%.",
            f"- Average suitability score: {avg_score}.",
            f"- Transactional repairs used: {snapshot.repairCount}.",
            f"- Open needs: {_count_needs(snapshot)}.",
            "- Recent decision traces:",
            *trace_lines,
            "- Bottleneck notes: check pending incidents, high route-risk zones, and low-fuel resources.",
        ]
    )
