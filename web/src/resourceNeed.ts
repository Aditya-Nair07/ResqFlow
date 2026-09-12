import type { Snapshot } from './api';

export type ResourceNeed = {
  waiting: number;
  depthCm: number;
  band: string;
  unit: string;
  reason: string;
  freeMatch: number;
};

function depthAt(snap: Snapshot, x: number, y: number) {
  const grid = snap.flood?.depthCm || [];
  const ix = Math.max(0, Math.min((snap.flood?.gridSize || 25) - 1, Math.round(x)));
  const iy = Math.max(0, Math.min((snap.flood?.gridSize || 25) - 1, Math.round(y)));
  return Number(grid[iy]?.[ix] || 0);
}

function unitKind(v: any) {
  const t = String(v.type || '').toLowerCase();
  if (v.mode === 'water' || t.includes('boat')) return 'boat';
  if (t.includes('truck') || t.includes('high')) return 'truck';
  return 'bus';
}

/** Same class rules as the plant: bus 25 cm, truck 45 cm, boat for water/closed road. */
export function resourceNeed(snap: Snapshot, group: any): ResourceNeed {
  const waiting = Math.max(0, (group.people || 0) - (group.evacuatedPeople || 0));
  const depthCm = Number(group.observedDepthCm ?? depthAt(snap, group.x, group.y));
  const wantBoat = group.requestedMode === 'water' || group.roadBlocked;
  const closed = (snap.closedEdgeIds || []).length > 0 && group.roadBlocked;

  let unit = 'Evacuation bus';
  let kind = 'bus';
  let band = 'Shallow';
  let reason = 'Roads are still bus-safe.';

  if (wantBoat || closed || depthCm >= 45) {
    unit = 'Rescue boat';
    kind = 'boat';
    band = depthCm >= 45 ? 'Deep / impassable' : 'Crew requested water';
    reason = wantBoat ? 'Crew asked for a boat.' : 'Too deep or road closed for buses and trucks.';
  } else if (depthCm >= 25) {
    unit = 'High-clearance truck';
    kind = 'truck';
    band = 'Knee-deep';
    reason = 'Too deep for a bus (25 cm limit).';
  } else if (depthCm >= 15) {
    band = 'Rising';
  }

  const seats = Math.max(1, waiting);
  const freeMatch = (snap.vehicles || []).filter((v) => {
    if (v.status !== 'available') return false;
    return unitKind(v) === kind;
  }).length;

  const extra = seats > 20 ? ' Large group — a second unit may follow after the first loads.' : '';
  const avail = freeMatch
    ? `${freeMatch} ${kind}${freeMatch === 1 ? '' : 's'} free.`
    : `No free ${kind} right now — Run will send one when a unit returns.`;

  return {
    waiting,
    depthCm: Math.round(depthCm),
    band,
    unit,
    reason: `${reason} ${avail}${extra}`.trim(),
    freeMatch,
  };
}
