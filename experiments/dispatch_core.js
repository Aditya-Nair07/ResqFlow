/**
 * ResQFlow dispatch core for reproducible offline benchmarks.
 * Formulas mirror index.html (Weighted / Ellipse / Polygon / Hybrid, GAPD, 8-check verify).
 * Agent council and LLM are excluded for determinism.
 */

"use strict";

const GRID_SIZE = 50;
const CPS_FUEL_RESERVE_AT_ARRIVAL = 5;
const CPS_URGENCY_ETA_BASE = 16;
const CPS_URGENCY_ETA_SCALE = 0.72;

const STRATEGY_WEIGHTS = {
  balanced: { urgency: 0.26, distance: 0.23, capability: 0.24, fuel: 0.14, risk: 0.13 }
};

const RESOURCE_TYPES = [
  { type: "Ambulance", capabilities: ["medical", "evacuation"], capacity: 2, speed: 1.35 },
  { type: "Rescue Boat", capabilities: ["flood", "evacuation"], capacity: 6, speed: 1.05 },
  { type: "Drone", capabilities: ["survey", "medical"], capacity: 1, speed: 1.8 },
  { type: "Food Truck", capabilities: ["food", "shelter"], capacity: 12, speed: 0.9 },
  { type: "Medical Team", capabilities: ["medical", "shelter"], capacity: 4, speed: 0.8 },
  { type: "Volunteer Team", capabilities: ["food", "evacuation", "shelter"], capacity: 8, speed: 0.95 }
];

function clamp(value, min, max) {
  return Math.max(min, Math.min(max, value));
}

function distance(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

function relatedNeeds(capability, need) {
  const pairs = {
    evacuation: ["flood", "medical", "shelter"],
    medical: ["evacuation", "shelter"],
    shelter: ["food", "evacuation"],
    food: ["shelter"],
    survey: ["flood", "evacuation"]
  };
  return (pairs[capability] || []).includes(need);
}

function getRouteRisk(from, to, riskZones) {
  let risk = 0;
  for (const zone of riskZones) {
    const midpoint = { x: (from.x + to.x) / 2, y: (from.y + to.y) / 2 };
    const distMid = Math.hypot(midpoint.x - zone.x, midpoint.y - zone.y);
    const distEnd = Math.hypot(to.x - zone.x, to.y - zone.y);
    const exposure = Math.max(0, zone.r + 4 - Math.min(distMid, distEnd));
    risk += exposure * (zone.level / 12);
  }
  return clamp(risk, 0, 100);
}

function nearestBase(resource, bases) {
  let best = bases[0];
  let bestDist = Infinity;
  for (const base of bases) {
    const d = distance(resource, base);
    if (d < bestDist) {
      bestDist = d;
      best = base;
    }
  }
  return best;
}

function getEllipseParams(resource, bases) {
  const focusA = nearestBase(resource, bases);
  const focusB = { x: resource.x, y: resource.y };
  const fociDist = distance(focusA, focusB);
  const reachBudget = (resource.fuel / 100) * 26 * clamp(resource.speed, 0.5, 2) + fociDist + 5;
  const twoA = Math.max(fociDist + 0.75, reachBudget);
  return { focusA, focusB, twoA, fociDist };
}

function scoreEllipseFit(resource, incident, bases) {
  const params = getEllipseParams(resource, bases);
  const sum = distance(incident, params.focusA) + distance(incident, params.focusB);
  const margin = params.twoA - sum;
  if (margin >= 0) {
    return clamp(Math.round(58 + (margin / params.twoA) * 42), 58, 100);
  }
  return clamp(Math.round(55 - ((-margin) / params.twoA) * 85), 0, 54);
}

function pointInRiskZone(x, y, riskZones, pad = 0.4) {
  return riskZones.some(zone => Math.hypot(x - zone.x, y - zone.y) <= zone.r + pad);
}

function cross(o, a, b) {
  return (a.x - o.x) * (b.y - o.y) - (a.y - o.y) * (b.x - o.x);
}

function convexHull(points) {
  const pts = points
    .map(p => ({ x: p.x, y: p.y }))
    .sort((a, b) => (a.x === b.x ? a.y - b.y : a.x - b.x));
  if (pts.length <= 1) return pts;
  const lower = [];
  for (const p of pts) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper = [];
  for (let i = pts.length - 1; i >= 0; i--) {
    const p = pts[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  upper.pop();
  lower.pop();
  return lower.concat(upper);
}

function pointInPolygon(point, polygon) {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;
    const intersect = ((yi > point.y) !== (yj > point.y))
      && (point.x < ((xj - xi) * (point.y - yi)) / ((yj - yi) || 1e-9) + xi);
    if (intersect) inside = !inside;
  }
  return inside;
}

function distanceToPolygonEdge(point, polygon) {
  if (polygon.length < 2) return distance(point, polygon[0] || point);
  let best = Infinity;
  for (let i = 0; i < polygon.length; i++) {
    const a = polygon[i];
    const b = polygon[(i + 1) % polygon.length];
    const abx = b.x - a.x;
    const aby = b.y - a.y;
    const len2 = abx * abx + aby * aby || 1e-9;
    let t = ((point.x - a.x) * abx + (point.y - a.y) * aby) / len2;
    t = clamp(t, 0, 1);
    const proj = { x: a.x + t * abx, y: a.y + t * aby };
    best = Math.min(best, distance(point, proj));
  }
  return best;
}

function buildServicePolygon(resource, riskZones) {
  const radius = (resource.fuel / 100) * 16 * clamp(resource.speed, 0.5, 2) + 5.5;
  const samples = [{ x: resource.x, y: resource.y }];
  const sectors = 18;
  for (let i = 0; i < sectors; i++) {
    const ang = (i / sectors) * Math.PI * 2;
    for (const frac of [0.45, 0.75, 1]) {
      const x = resource.x + Math.cos(ang) * radius * frac;
      const y = resource.y + Math.sin(ang) * radius * frac;
      if (x < 1 || y < 1 || x > GRID_SIZE - 1 || y > GRID_SIZE - 1) continue;
      if (pointInRiskZone(x, y, riskZones)) continue;
      const tip = { x, y };
      if (getRouteRisk(resource, tip, riskZones) >= 70) continue;
      samples.push(tip);
    }
  }
  const hull = convexHull(samples);
  return hull.length >= 3 ? hull : samples.slice(0, Math.min(samples.length, 3));
}

function scorePolygonFit(resource, incident, riskZones) {
  const poly = buildServicePolygon(resource, riskZones);
  if (poly.length < 3) return 8;
  if (pointInPolygon(incident, poly)) {
    const depth = distanceToPolygonEdge(incident, poly);
    return clamp(Math.round(62 + depth * 7), 62, 100);
  }
  const gap = distanceToPolygonEdge(incident, poly);
  return clamp(Math.round(52 - gap * 3.8), 0, 51);
}

function priorityBand(urgency) {
  if (urgency >= 90) return 3;
  if (urgency >= 75) return 2;
  if (urgency >= 55) return 1;
  return 0;
}

function gapdPriorityKey(incident, geometryScore = 50) {
  const band = priorityBand(incident.urgency);
  const peoplePressure = clamp(incident.people * 5, 0, 100);
  return 1000 * band + 0.45 * geometryScore + 0.35 * incident.urgency + 0.20 * peoplePressure;
}

function geometryScoreForMethod(resource, incident, method, bases, riskZones) {
  if (method === "ellipse") return scoreEllipseFit(resource, incident, bases);
  if (method === "polygon") return scorePolygonFit(resource, incident, riskZones);
  if (method === "hybrid") {
    return Math.round(
      0.5 * scoreEllipseFit(resource, incident, bases) +
      0.5 * scorePolygonFit(resource, incident, riskZones)
    );
  }
  return clamp(100 - distance(resource, incident) * 2.1, 0, 100);
}

function estimateTravelTicks(dist, resourceSpeed) {
  const routeSteps = Math.max(6, Math.ceil(dist));
  return Math.ceil(routeSteps / clamp(resourceSpeed || 1, 0.5, 2));
}

function fuelAtArrival(resource, fuelCost) {
  return clamp(resource.fuel - fuelCost, 0, 100);
}

function urgencyMaxTicks(urgency) {
  return Math.round(CPS_URGENCY_ETA_BASE + (100 - urgency) * CPS_URGENCY_ETA_SCALE);
}

function softReservedForCritical(ctx, resource, forIncident) {
  if (!ctx.useGapdPriority) return false;
  if (priorityBand(forIncident.urgency) >= 3) return false;
  const criticals = ctx.incidents.filter(
    item => item.status === "pending" && priorityBand(item.urgency) >= 3 && item.id !== forIncident.id
  );
  if (!criticals.length) return false;

  for (const crit of criticals) {
    const capable = ctx.resources.filter(r => {
      if (r.status !== "available") return false;
      return r.capabilities.includes(crit.need)
        || r.capabilities.some(cap => relatedNeeds(cap, crit.need));
    });
    if (!capable.some(r => r.id === resource.id)) continue;
    if (capable.length <= 2) return true;
    const ranked = capable
      .map(r => ({
        id: r.id,
        g: geometryScoreForMethod(r, crit, ctx.rankingMethod, ctx.bases, ctx.riskZones)
      }))
      .sort((a, b) => b.g - a.g);
    if (ranked[0]?.id === resource.id || ranked[1]?.id === resource.id) return true;
  }
  return false;
}

function scoreResource(ctx, resource, incident, options = {}) {
  const dist = distance(resource, incident);
  const routeRisk = getRouteRisk(resource, incident, ctx.riskZones);
  const capabilityScore = resource.capabilities.includes(incident.need)
    ? 100
    : resource.capabilities.some(cap => relatedNeeds(cap, incident.need))
      ? 62
      : 18;
  const capacityScore = clamp((resource.capacity / Math.max(incident.people, 1)) * 100, 20, 100);
  const distanceScore = clamp(100 - dist * 2.1, 0, 100);
  const urgencyScore = incident.urgency;
  const fuelCost = Math.ceil(dist / 2.5);
  const fuelScore = resource.fuel > fuelCost + 8 ? clamp(resource.fuel - fuelCost, 0, 100) : 8;
  const riskScore = clamp(100 - routeRisk, 0, 100);
  const availabilityPenalty = resource.status === "available" ? 0 : 45;
  const capabilityCombined = capabilityScore * 0.78 + capacityScore * 0.22;
  const weights = STRATEGY_WEIGHTS.balanced;
  const weightedTotal = (
    urgencyScore * weights.urgency +
    distanceScore * weights.distance +
    capabilityCombined * weights.capability +
    fuelScore * weights.fuel +
    riskScore * weights.risk
  ) - availabilityPenalty;

  const ellipseScore = scoreEllipseFit(resource, incident, ctx.bases);
  const polygonScore = scorePolygonFit(resource, incident, ctx.riskZones);
  const method = options.method || ctx.rankingMethod || "weighted";

  let total;
  if (method === "ellipse") {
    total = ellipseScore * 0.55 + capabilityCombined * 0.25 + urgencyScore * 0.10 + riskScore * 0.10
      - availabilityPenalty;
  } else if (method === "polygon") {
    total = polygonScore * 0.55 + capabilityCombined * 0.25 + urgencyScore * 0.10 + riskScore * 0.10
      - availabilityPenalty;
  } else if (method === "hybrid") {
    total = weightedTotal * 0.40 + ellipseScore * 0.30 + polygonScore * 0.30;
  } else {
    total = weightedTotal;
  }

  if (softReservedForCritical(ctx, resource, incident)) total -= 42;

  const verification = verifyCandidate(ctx, resource, incident, {
    fuelCost,
    capabilityScore,
    routeRisk,
    dist,
    skipPriorityGate: options.skipPriorityGate
  });

  return {
    total: clamp(Math.round(total), 0, 100),
    distance: Math.round(dist),
    routeRisk: Math.round(routeRisk),
    fuelCost,
    canCommit: verification.passed,
    checksPassed: verification.passed,
    failed: verification.failed
  };
}

function incidentHasSafeResource(ctx, incident) {
  return ctx.resources.some(resource =>
    scoreResource(ctx, resource, incident, { skipPriorityGate: true, method: ctx.rankingMethod }).canCommit
  );
}

function hasHigherPriorityPending(ctx, incident) {
  return ctx.incidents.some(item =>
    item.status === "pending" &&
    item.id !== incident.id &&
    item.urgency >= 90 &&
    item.urgency > incident.urgency + 12 &&
    incidentHasSafeResource(ctx, item)
  );
}

function verifyCandidate(ctx, resource, incident, details) {
  const dist = details.dist ?? distance(resource, incident);
  const etaTicks = estimateTravelTicks(dist, resource.speed);
  const projectedFuel = fuelAtArrival(resource, details.fuelCost);
  const maxEta = urgencyMaxTicks(incident.urgency);

  const checks = [
    { label: "resource available", passed: resource.status === "available" },
    { label: "fuel margin sufficient", passed: resource.fuel > details.fuelCost + 8 },
    { label: "capability acceptable", passed: details.capabilityScore >= 50 },
    { label: "route risk acceptable", passed: details.routeRisk < 72 },
    { label: "not double-booked", passed: !resource.assignedIncidentId },
    { label: "high-priority request not ignored", passed: details.skipPriorityGate || !hasHigherPriorityPending(ctx, incident) },
    { label: "fuel sufficient at arrival", passed: projectedFuel >= CPS_FUEL_RESERVE_AT_ARRIVAL },
    { label: "ETA within urgency window", passed: etaTicks <= maxEta }
  ];
  return {
    passed: checks.every(check => check.passed),
    failed: checks.filter(check => !check.passed).map(check => check.label)
  };
}

function findActuationWinner(bids, closedLoop) {
  if (closedLoop) {
    return bids.find(bid => bid.score.canCommit) || null;
  }
  return bids.find(bid =>
    bid.resource.status === "available" && !bid.resource.assignedIncidentId
  ) || null;
}

/**
 * Run one first-wave dispatch experiment (no movement / completion).
 * Resources stay assigned after actuation so the wave measures initial safe allocation.
 */
function runDispatchExperiment(config) {
  const ctx = {
    bases: config.bases.map(b => ({ ...b })),
    riskZones: config.riskZones.map(z => ({ ...z })),
    resources: config.resources.map(r => ({ ...r, status: "available", assignedIncidentId: null })),
    incidents: config.incidents.map(i => ({ ...i, status: "pending", assignedResourceId: null })),
    rankingMethod: config.rankingMethod,
    useGapdPriority: config.useGapdPriority,
    closedLoopControl: config.closedLoopControl
  };

  const metrics = {
    assignments: 0,
    repairs: 0,
    unsafe_actuations: 0,
    distances: [],
    risks: [],
    fuelCosts: [],
    critical_served: 0
  };

  const maxRounds = config.maxRounds ?? 5;
  for (let round = 0; round < maxRounds; round++) {
    const pending = ctx.incidents.filter(i => i.status === "pending");
    if (!pending.length) break;

    const ordered = [...pending].sort((a, b) => {
      if (ctx.useGapdPriority) {
        const geoA = Math.max(
          0,
          ...ctx.resources
            .filter(r => r.status === "available")
            .map(r => geometryScoreForMethod(r, a, ctx.rankingMethod, ctx.bases, ctx.riskZones))
        );
        const geoB = Math.max(
          0,
          ...ctx.resources
            .filter(r => r.status === "available")
            .map(r => geometryScoreForMethod(r, b, ctx.rankingMethod, ctx.bases, ctx.riskZones))
        );
        return gapdPriorityKey(b, geoB) - gapdPriorityKey(a, geoA);
      }
      return b.urgency - a.urgency;
    });

    let madeProgress = false;
    for (const incident of ordered.slice(0, 2)) {
      const bids = ctx.resources
        .map(resource => ({
          resource,
          score: scoreResource(ctx, resource, incident, { method: ctx.rankingMethod })
        }))
        .sort((a, b) => b.score.total - a.score.total);

      if (!bids.length) continue;
      const initial = bids[0];
      const winner = findActuationWinner(bids, ctx.closedLoopControl);
      if (!winner) continue;

      if (ctx.closedLoopControl && initial.resource.id !== winner.resource.id) {
        metrics.repairs += 1;
      }
      if (!ctx.closedLoopControl && !winner.score.canCommit) {
        metrics.unsafe_actuations += 1;
      }

      incident.status = "assigned";
      incident.assignedResourceId = winner.resource.id;
      winner.resource.status = "assigned";
      winner.resource.assignedIncidentId = incident.id;
      winner.resource.fuel = clamp(winner.resource.fuel - winner.score.fuelCost, 0, 100);

      metrics.assignments += 1;
      metrics.distances.push(winner.score.distance);
      metrics.risks.push(winner.score.routeRisk);
      metrics.fuelCosts.push(winner.score.fuelCost);
      if (priorityBand(incident.urgency) >= 3) metrics.critical_served += 1;
      madeProgress = true;
    }
    if (!madeProgress) break;
  }

  const n = metrics.assignments || 1;
  return {
    assignments: metrics.assignments,
    repairs: metrics.repairs,
    unsafe_actuations: metrics.unsafe_actuations,
    avg_distance: metrics.assignments
      ? Math.round((metrics.distances.reduce((a, b) => a + b, 0) / metrics.assignments) * 100) / 100
      : 0,
    avg_route_risk: metrics.assignments
      ? Math.round((metrics.risks.reduce((a, b) => a + b, 0) / metrics.assignments) * 100) / 100
      : 0,
    total_fuel_cost: metrics.fuelCosts.reduce((a, b) => a + b, 0),
    critical_served: metrics.critical_served
  };
}

module.exports = {
  RESOURCE_TYPES,
  runDispatchExperiment,
  priorityBand,
  SEED_NOTE: "Benchmarks use fixed layouts and fixed fuel; no Math.random."
};
