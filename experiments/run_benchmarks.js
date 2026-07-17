#!/usr/bin/env node
/**
 * Reproducible ResQFlow dispatch benchmarks.
 * Usage: node experiments/run_benchmarks.js
 * Writes: experiments/results/benchmark_results.csv
 */

"use strict";

const fs = require("fs");
const path = require("path");
const { RESOURCE_TYPES, runDispatchExperiment } = require("./dispatch_core");

const SEED = 42; // layout seed label only — layouts are fully fixed (no RNG)
const MAX_ROUNDS = 5;

const BASES = [
  { x: 5, y: 5, label: "North Base" },
  { x: 45, y: 7, label: "Medical Depot" },
  { x: 8, y: 44, label: "Relief Hub" },
  { x: 43, y: 43, label: "Rescue Camp" }
];

const RISK_DEFAULT = [
  { x: 25, y: 18, r: 6, level: 72, label: "Flooded road" },
  { x: 35, y: 32, r: 5, level: 64, label: "Debris zone" },
  { x: 15, y: 29, r: 4, level: 58, label: "Congestion" }
];

const RISK_HEAVY = [
  { x: 25, y: 18, r: 8, level: 85, label: "Flooded road" },
  { x: 35, y: 32, r: 7, level: 80, label: "Debris zone" },
  { x: 15, y: 29, r: 6, level: 75, label: "Congestion" },
  { x: 30, y: 12, r: 5, level: 70, label: "Washout" }
];

const RESOURCE_PLACEMENTS = [
  { x: 5, y: 5 }, { x: 7, y: 8 }, { x: 45, y: 7 },
  { x: 43, y: 43 }, { x: 8, y: 44 }, { x: 11, y: 41 },
  { x: 46, y: 11 }, { x: 4, y: 39 }
];

function makeResources(fuel = 90) {
  return RESOURCE_PLACEMENTS.map((pos, index) => {
    const def = RESOURCE_TYPES[index % RESOURCE_TYPES.length];
    return {
      id: index + 1,
      type: def.type,
      capabilities: [...def.capabilities],
      capacity: def.capacity,
      speed: def.speed,
      x: pos.x,
      y: pos.y,
      fuel
    };
  });
}

const SCENES = {
  default: {
    bases: BASES,
    riskZones: RISK_DEFAULT,
    resources: makeResources(90),
    incidents: [
      { id: 1, type: "Flood Rescue", need: "flood", urgency: 96, people: 6, x: 24, y: 17 },
      { id: 2, type: "Medical Emergency", need: "medical", urgency: 91, people: 3, x: 42, y: 10 },
      { id: 3, type: "Food Delivery", need: "food", urgency: 58, people: 14, x: 10, y: 41 },
      { id: 4, type: "Shelter Overflow", need: "shelter", urgency: 74, people: 20, x: 36, y: 36 },
      { id: 5, type: "Evacuation Help", need: "evacuation", urgency: 82, people: 7, x: 14, y: 20 }
    ]
  },
  risk_heavy: {
    bases: BASES,
    riskZones: RISK_HEAVY,
    resources: makeResources(70),
    incidents: [
      { id: 1, type: "Flood Rescue", need: "flood", urgency: 97, people: 8, x: 26, y: 19 },
      { id: 2, type: "Medical Emergency", need: "medical", urgency: 93, people: 4, x: 34, y: 30 },
      { id: 3, type: "Food Delivery", need: "food", urgency: 60, people: 16, x: 16, y: 28 },
      { id: 4, type: "Shelter Overflow", need: "shelter", urgency: 76, people: 22, x: 32, y: 14 },
      { id: 5, type: "Evacuation Help", need: "evacuation", urgency: 85, people: 9, x: 28, y: 22 }
    ]
  },
  sparse: {
    bases: BASES,
    riskZones: RISK_DEFAULT,
    resources: makeResources(85),
    incidents: [
      { id: 1, type: "Flood Rescue", need: "flood", urgency: 95, people: 5, x: 28, y: 28 },
      { id: 2, type: "Medical Emergency", need: "medical", urgency: 92, people: 2, x: 20, y: 35 },
      { id: 3, type: "Food Delivery", need: "food", urgency: 55, people: 12, x: 38, y: 8 },
      { id: 4, type: "Shelter Overflow", need: "shelter", urgency: 70, people: 18, x: 12, y: 12 },
      { id: 5, type: "Evacuation Help", need: "evacuation", urgency: 80, people: 6, x: 40, y: 40 }
    ]
  },
  // Distant critical jobs + low fuel → verification failures likely; open-loop may still actuate.
  stress: {
    bases: BASES,
    riskZones: RISK_HEAVY,
    resources: makeResources(35),
    incidents: [
      { id: 1, type: "Flood Rescue", need: "flood", urgency: 98, people: 10, x: 30, y: 30 },
      { id: 2, type: "Medical Emergency", need: "medical", urgency: 96, people: 5, x: 25, y: 35 },
      { id: 3, type: "Food Delivery", need: "food", urgency: 50, people: 20, x: 8, y: 42 },
      { id: 4, type: "Shelter Overflow", need: "shelter", urgency: 72, people: 25, x: 40, y: 40 },
      { id: 5, type: "Evacuation Help", need: "evacuation", urgency: 88, people: 12, x: 18, y: 18 }
    ]
  }
};

function buildCases() {
  const cases = [];

  // Method comparison on default scene (closed + GAPD)
  for (const method of ["weighted", "ellipse", "polygon", "hybrid"]) {
    cases.push({
      case_id: `method_${method}`,
      ranking_method: method,
      control_mode: "closed",
      priority_mode: "gapd",
      scene: "default"
    });
  }

  // Closed vs open (hybrid + GAPD on default)
  cases.push({
    case_id: "control_closed",
    ranking_method: "hybrid",
    control_mode: "closed",
    priority_mode: "gapd",
    scene: "default"
  });
  cases.push({
    case_id: "control_open",
    ranking_method: "hybrid",
    control_mode: "open",
    priority_mode: "gapd",
    scene: "default"
  });

  // Closed vs open under stress (low fuel + hard routes) — expected unsafe contrast
  cases.push({
    case_id: "control_closed_stress",
    ranking_method: "hybrid",
    control_mode: "closed",
    priority_mode: "gapd",
    scene: "stress"
  });
  cases.push({
    case_id: "control_open_stress",
    ranking_method: "hybrid",
    control_mode: "open",
    priority_mode: "gapd",
    scene: "stress"
  });

  // GAPD vs urgency-only (hybrid + closed on default)
  cases.push({
    case_id: "priority_gapd",
    ranking_method: "hybrid",
    control_mode: "closed",
    priority_mode: "gapd",
    scene: "default"
  });
  cases.push({
    case_id: "priority_urgency",
    ranking_method: "hybrid",
    control_mode: "closed",
    priority_mode: "urgency",
    scene: "default"
  });

  // Scene variants (hybrid + closed + GAPD)
  for (const scene of ["default", "risk_heavy", "sparse", "stress"]) {
    cases.push({
      case_id: `scene_${scene}`,
      ranking_method: "hybrid",
      control_mode: "closed",
      priority_mode: "gapd",
      scene
    });
  }

  return cases;
}

function runCase(spec) {
  const scene = SCENES[spec.scene];
  const result = runDispatchExperiment({
    bases: scene.bases,
    riskZones: scene.riskZones,
    resources: scene.resources,
    incidents: scene.incidents,
    rankingMethod: spec.ranking_method,
    useGapdPriority: spec.priority_mode === "gapd",
    closedLoopControl: spec.control_mode === "closed",
    maxRounds: MAX_ROUNDS
  });

  return {
    case_id: spec.case_id,
    ranking_method: spec.ranking_method,
    control_mode: spec.control_mode,
    priority_mode: spec.priority_mode,
    scene: spec.scene,
    seed: SEED,
    assignments: result.assignments,
    repairs: result.repairs,
    unsafe_actuations: result.unsafe_actuations,
    avg_distance: result.avg_distance,
    avg_route_risk: result.avg_route_risk,
    total_fuel_cost: result.total_fuel_cost,
    critical_served: result.critical_served
  };
}

function toCsv(rows) {
  const headers = [
    "case_id",
    "ranking_method",
    "control_mode",
    "priority_mode",
    "scene",
    "seed",
    "assignments",
    "repairs",
    "unsafe_actuations",
    "avg_distance",
    "avg_route_risk",
    "total_fuel_cost",
    "critical_served"
  ];
  const lines = [headers.join(",")];
  for (const row of rows) {
    lines.push(headers.map(h => row[h]).join(","));
  }
  return `${lines.join("\n")}\n`;
}

function main() {
  const cases = buildCases();
  const rows = cases.map(runCase);
  const outDir = path.join(__dirname, "results");
  fs.mkdirSync(outDir, { recursive: true });
  const outPath = path.join(outDir, "benchmark_results.csv");
  fs.writeFileSync(outPath, toCsv(rows), "utf8");

  console.log(`Wrote ${rows.length} rows → ${outPath}`);
  console.table(rows.map(r => ({
    case_id: r.case_id,
    assignments: r.assignments,
    repairs: r.repairs,
    unsafe: r.unsafe_actuations,
    avg_dist: r.avg_distance,
    avg_risk: r.avg_route_risk,
    fuel: r.total_fuel_cost,
    critical: r.critical_served
  })));
}

main();
