/** Format plant events into a short, readable ops log. */

export type PlantEvent = {
  seq?: number;
  type?: string;
  tick?: number;
  at?: string;
  payload?: Record<string, unknown>;
};

export type FeedRow = {
  key: string;
  tick: number;
  tone: 'mint' | 'amber' | 'coral' | 'muted';
  tag: string;
  text: string;
};

/** Only these types appear in the desk log — keeps noise out. */
export const FEED_TYPES = new Set([
  'report_received',
  'unit_assigned',
  'field_update',
  'road_closed',
  'stand_down',
  'group_stranded',
  'replan_required',
  'weather_updated',
  'shelter_status_changed',
]);

function pay(e: PlantEvent): Record<string, unknown> {
  return (e.payload || {}) as Record<string, unknown>;
}

export function formatFeedRow(e: PlantEvent): FeedRow | null {
  const type = String(e.type || '');
  if (!FEED_TYPES.has(type)) return null;
  const p = pay(e);
  const tick = Number(e.tick ?? 0);
  const key = String(e.seq ?? `${type}-${tick}`);

  switch (type) {
    case 'report_received': {
      const people = Number(p.people || 0);
      const place = String(p.landmark || p.area || p.groupId || 'new pin');
      if (people > 0) {
        return { key, tick, tone: 'coral', tag: 'REPORT', text: `Rescue ask · ${people} people · ${place}` };
      }
      return { key, tick, tone: 'amber', tag: 'REPORT', text: `Waterlogging noted · ${place}` };
    }
    case 'unit_assigned': {
      const unit = p.vehicleType ? `${p.vehicleType} ${p.vehicleId}` : `Unit ${p.vehicleId}`;
      const where = String(p.groupLabel || p.groupId || 'group');
      const load = p.load != null ? ` · ${p.load} aboard` : '';
      return { key, tick, tone: 'mint', tag: 'DISPATCH', text: `${unit} → ${where}${load}` };
    }
    case 'field_update': {
      const action = String(p.action || 'field update');
      const note = p.note ? ` · ${String(p.note).slice(0, 48)}` : '';
      const tone = action.includes('clear') ? 'amber' : action.includes('blocked') ? 'coral' : 'amber';
      return { key, tick, tone, tag: 'CREW', text: `${action}${note}` };
    }
    case 'road_closed':
      return {
        key,
        tick,
        tone: 'coral',
        tag: 'ROAD',
        text: `Edge closed${p.edgeId ? ` · ${p.edgeId}` : ''}`,
      };
    case 'stand_down':
      return {
        key,
        tick,
        tone: 'amber',
        tag: 'CLEAR',
        text: `Stand-down · ${p.groupId || 'site'} · ${p.action || 'recalled'}`,
      };
    case 'group_stranded':
      return {
        key,
        tick,
        tone: 'coral',
        tag: 'ALERT',
        text: `Stranded · ${p.groupId || 'group'} past deadline`,
      };
    case 'replan_required':
      return {
        key,
        tick,
        tone: 'amber',
        tag: 'REPLAN',
        text: String(p.reason || p.groupId || 'Plan needs refresh'),
      };
    case 'weather_updated':
      return { key, tick, tone: 'muted', tag: 'WEATHER', text: 'Rainfall / weather pulse applied' };
    case 'shelter_status_changed':
      return {
        key,
        tick,
        tone: 'amber',
        tag: 'SHELTER',
        text: `${p.id || 'shelter'} · occ ${p.occupancy ?? '—'}`,
      };
    default:
      return null;
  }
}

/** Newest first, capped — desk stays calm. */
export function buildEventFeed(events: PlantEvent[] | undefined, limit = 8): FeedRow[] {
  const rows: FeedRow[] = [];
  const list = [...(events || [])].sort((a, b) => Number(b.seq || 0) - Number(a.seq || 0));
  for (const e of list) {
    const row = formatFeedRow(e);
    if (!row) continue;
    rows.push(row);
    if (rows.length >= limit) break;
  }
  return rows;
}
