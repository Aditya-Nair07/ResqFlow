/** API client for unified ResQFlow-Flood Operations Desk. */

const API = import.meta.env.VITE_API_URL ?? '';

async function jsonFetch(path: string, init?: RequestInit) {
  const response = await fetch(`${API}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
    ...init,
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`${response.status}: ${detail}`);
  }
  return response.json();
}

export type Snapshot = {
  scenarioId: string;
  tick: number;
  flood: { depthCm: number[][]; maxDepthCm: number; gridSize: number };
  groups: any[];
  vehicles: any[];
  shelters: any[];
  reports: any[];
  events: any[];
  metrics: Record<string, number>;
  rankingMethod: string;
  closedLoop: boolean;
  roadEdgeStates: any[];
  recentTraces: any[];
  weather?: any;
  planVersion?: number;
  lastCitizenReport?: any;
  difficulty?: string;
  fixtureMeta?: {
    label?: string;
    note?: string;
    shelterCount?: number;
    reportCount?: number;
    areas?: string[];
  } | null;
  rainfallPerTick?: number;
  fieldUpdates?: any[];
  reservations?: any[];
};

export const api = {
  reset: (scenarioId: string, difficulty = 'normal') =>
    jsonFetch(`/flood/reset?scenarioId=${encodeURIComponent(scenarioId)}&difficulty=${encodeURIComponent(difficulty)}`, {
      method: 'POST',
    }),
  snapshot: (scenarioId: string) => jsonFetch(`/flood/snapshot?scenarioId=${encodeURIComponent(scenarioId)}`) as Promise<Snapshot>,
  step: (body: Record<string, unknown>) => jsonFetch('/flood/simulate/step', { method: 'POST', body: JSON.stringify(body) }),
  citizenReport: (body: Record<string, unknown>) => jsonFetch('/flood/reports/citizen', { method: 'POST', body: JSON.stringify(body) }),
  operatorUpdate: (body: Record<string, unknown>) => jsonFetch('/flood/reports/operator', { method: 'POST', body: JSON.stringify(body) }),
  fieldUpdate: (body: Record<string, unknown>) => jsonFetch('/flood/field-updates', { method: 'POST', body: JSON.stringify(body) }),
  verify: (id: string, body: Record<string, unknown>) => jsonFetch(`/flood/incidents/${id}/verify`, { method: 'POST', body: JSON.stringify(body) }),
  prioritize: (id: string, body: Record<string, unknown>) => jsonFetch(`/flood/incidents/${id}/prioritize`, { method: 'POST', body: JSON.stringify(body) }),
  comparePlans: (body: Record<string, unknown>) => jsonFetch('/flood/plans/compare', { method: 'POST', body: JSON.stringify(body) }),
  approvePlan: (planId: string, body: Record<string, unknown>) => jsonFetch(`/flood/plans/${planId}/approve`, { method: 'POST', body: JSON.stringify(body) }),
  replan: (body: Record<string, unknown>) => jsonFetch('/flood/replan', { method: 'POST', body: JSON.stringify(body) }),
  weather: (body: Record<string, unknown>) => jsonFetch('/flood/weather', { method: 'POST', body: JSON.stringify(body) }),
  difficulty: (body: Record<string, unknown>) => jsonFetch('/flood/difficulty', { method: 'POST', body: JSON.stringify(body) }),
  chennaiFixtures: () => jsonFetch('/flood/chennai/fixtures'),
  events: (scenarioId: string, after = 0) => jsonFetch(`/flood/events?scenarioId=${encodeURIComponent(scenarioId)}&after=${after}`),
  scenarios: () => jsonFetch('/flood/scenarios'),
};

export { API };
