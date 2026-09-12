/** Pure helpers for Ops Desk evidence + decision panels. Keep copy short. */

export type AuditEntry = {
  at?: string;
  action?: string;
  actor?: string;
  detail?: string;
};

export type DecisionRecord = {
  tick?: number;
  vehicleId?: number | string;
  vehicleType?: string;
  shelterId?: string;
  shelterLabel?: string;
  methodLabel?: string;
  method?: string;
  score?: number;
  load?: number;
  checksPassed?: number;
  checksTotal?: number;
  summary?: string;
  gapdScore?: number;
  rejected?: Array<{
    vehicleId?: number | string;
    vehicleType?: string;
    reason?: string;
    failed?: string[];
  }>;
  checks?: Array<{ label?: string; passed?: boolean }>;
};

export function sourceLabel(source?: string): string {
  switch (String(source || '').toUpperCase()) {
    case 'CITIZEN':
      return 'Citizen report';
    case 'FIELD_TEAM':
      return 'Field crew';
    case 'WARD_VOLUNTEER':
      return 'Ward volunteer';
    case 'OPERATOR':
      return 'Control room';
    case 'SIMULATOR':
      return 'Scenario seed';
    default:
      return source || 'Unknown source';
  }
}

/** Trust band for a quiet chip — never claims KYC, only demo trust. */
export function trustBand(trust?: number): { label: string; tone: 'high' | 'mid' | 'low' } {
  const t = Number(trust ?? 0);
  if (t >= 80) return { label: 'High trust', tone: 'high' };
  if (t >= 55) return { label: 'Medium trust', tone: 'mid' };
  return { label: 'Lower trust', tone: 'low' };
}

export function recentAudit(audit: AuditEntry[] | undefined, limit = 4): AuditEntry[] {
  if (!Array.isArray(audit) || !audit.length) return [];
  return audit.slice(-limit);
}

export function formatAuditTime(at?: string): string {
  if (!at) return '—';
  if (at.startsWith('tick-')) return at.replace('tick-', 't');
  // ISO → HH:MM
  const m = at.match(/T(\d{2}:\d{2})/);
  return m ? m[1] : at.slice(0, 16);
}

/** Prefer group.lastDecision; fall back to latest matching recentTrace. */
export function resolveDecision(
  group: { id?: string; lastDecision?: DecisionRecord | null },
  recentTraces?: Array<{ groupId?: string; decision?: DecisionRecord; vehicleId?: unknown; shelterId?: string; score?: number; method?: string; verification?: { load?: number; checks?: Array<{ label?: string; passed?: boolean }> } }>,
): DecisionRecord | null {
  if (group?.lastDecision && group.lastDecision.vehicleId != null) {
    return group.lastDecision;
  }
  const traces = recentTraces || [];
  for (let i = traces.length - 1; i >= 0; i -= 1) {
    const t = traces[i];
    if (t.groupId !== group.id) continue;
    if (t.decision) return t.decision;
    const checks = t.verification?.checks || [];
    return {
      vehicleId: t.vehicleId as string | number,
      shelterId: t.shelterId,
      score: typeof t.score === 'number' ? Math.round(t.score * 10) / 10 : undefined,
      method: t.method,
      load: t.verification?.load,
      checksPassed: checks.filter((c) => c.passed).length,
      checksTotal: checks.length || undefined,
      checks,
      summary: `Unit ${t.vehicleId} → ${t.shelterId}`,
    };
  }
  return null;
}

export function rejectedLine(decision: DecisionRecord | null): string | null {
  const r = decision?.rejected?.[0];
  if (!r) return null;
  const who = r.vehicleType ? `${r.vehicleType} ${r.vehicleId ?? ''}`.trim() : `Unit ${r.vehicleId}`;
  return `Passed over ${who} — ${r.reason || 'failed safety check'}`;
}
