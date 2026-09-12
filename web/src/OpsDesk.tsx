import { api, type Snapshot } from './api';
import { resourceNeed } from './resourceNeed';
import {
  formatAuditTime,
  recentAudit,
  rejectedLine,
  resolveDecision,
  sourceLabel,
  trustBand,
} from './decisionExplain';

function statusLabel(status: string) {
  const s = String(status || '').toLowerCase();
  if (s.includes('evacuat') || s === 'resolved') return 'Rescued';
  if (s.includes('strand')) return 'Stranded';
  if (s.includes('assign') || s.includes('dispatch') || s.includes('progress')) return 'En route';
  if (s.includes('report') || s.includes('verif') || s.includes('prior') || s === 'pending') return 'Needs help';
  return status;
}

export default function OpsDesk({
  snap,
  scenarioId,
  selectedId,
  onSelect,
  onChange,
}: {
  snap: Snapshot;
  scenarioId: string;
  selectedId: string | null;
  onSelect: (id: string) => void;
  onChange: (message: string) => Promise<void>;
}) {
  const selected = snap.groups.find((g) => g.id === selectedId) || snap.groups[0];
  const waiting = snap.groups.filter((g) => !['evacuated', 'RESOLVED', 'REJECTED'].includes(g.status));
  const need = selected ? resourceNeed(snap, selected) : null;
  const cleared = selected && ['evacuated', 'RESOLVED', 'REJECTED'].includes(selected.status);

  const trust = selected ? trustBand(selected.trust) : null;
  const audit = selected ? recentAudit(selected.audit, 4) : [];
  const decision = selected ? resolveDecision(selected, snap.recentTraces) : null;
  const passedOver = rejectedLine(decision);
  const showWhy = Boolean(decision && selected?.assignedVehicleId);

  async function crew(body: Record<string, unknown>, message: string) {
    if (!selected) return;
    await api.fieldUpdate({
      scenarioId,
      groupId: selected.id,
      actor: 'field_team',
      source: 'FIELD_TEAM',
      ...body,
    });
    await onChange(message);
  }

  return (
    <div className="incident-desk review-desk">
      <div className="desk-heading">
        <div>
          <p className="eyebrow">WHO NEEDS HELP</p>
          <h2>People at risk</h2>
          <span>{waiting.length} groups still need rescue</span>
        </div>
      </div>
      <div className="incident-layout review-incident-layout">
        <div className="incident-queue">
          {snap.groups.map((g) => (
            <button
              key={g.id}
              type="button"
              className={`incident-card ${selected?.id === g.id ? 'selected' : ''}`}
              onClick={() => onSelect(g.id)}
            >
              <div className="incident-card-top">
                <b>{g.label || g.area || g.id}</b>
                <span className={`severity ${(g.severity || 'MEDIUM').toLowerCase()}`}>
                  {g.severity || 'MEDIUM'}
                </span>
              </div>
              <small>
                {g.people} people · {statusLabel(g.status)}
                {typeof g.trust === 'number' ? ` · trust ${g.trust}` : ''}
              </small>
            </button>
          ))}
        </div>
        {selected && (
          <div className="incident-detail">
            <div className="detail-heading">
              <div>
                <h3>{selected.label || selected.id}</h3>
                <p>{selected.area || selected.landmark || 'Flood-affected group'}</p>
              </div>
              <div className="status-pill">{statusLabel(selected.status)}</div>
            </div>
            <div className="detail-grid review-detail-grid">
              <div><small>PEOPLE</small><p>{selected.people}</p></div>
              <div><small>STILL WAITING</small><p>{need?.waiting ?? 0}</p></div>
              <div>
                <small>VEHICLE</small>
                <p>{selected.assignedVehicleId ? `Unit ${selected.assignedVehicleId}` : 'Not assigned'}</p>
              </div>
              <div>
                <small>SHELTER</small>
                <p>{selected.assignedShelterId || 'Not assigned'}</p>
              </div>
            </div>

            {need && !cleared && (
              <div className="resource-card">
                <small>RESOURCE NEEDED</small>
                <strong>{need.unit}</strong>
                <p>{need.band} · {need.depthCm} cm at pin. {need.reason}</p>
              </div>
            )}

            <div className="evidence-block">
              <small>EVIDENCE</small>
              <div className="evidence-line">
                <span>{sourceLabel(selected.source)}</span>
                {trust && <span className={`trust-chip ${trust.tone}`}>{trust.label} · {selected.trust ?? '—'}</span>}
                {typeof selected.confidenceScore === 'number' && (
                  <span className="evidence-meta">confidence {selected.confidenceScore}</span>
                )}
                {typeof selected.gapdScore === 'number' && (
                  <span className="evidence-meta">GAPD {selected.gapdScore}</span>
                )}
              </div>
              {audit.length > 0 ? (
                <ul className="audit-list">
                  {audit.map((row, idx) => (
                    <li key={`${row.at}-${row.action}-${idx}`}>
                      <time>{formatAuditTime(row.at)}</time>
                      <span>
                        <b>{row.action}</b>
                        {row.detail ? ` — ${row.detail}` : ''}
                        {row.actor ? ` · ${row.actor}` : ''}
                      </span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="evidence-empty">No field notes yet.</p>
              )}
            </div>

            {showWhy && decision && (
              <div className="why-block">
                <small>WHY THIS UNIT</small>
                <strong>
                  {decision.vehicleType || 'Unit'} {decision.vehicleId}
                  {decision.shelterLabel || decision.shelterId
                    ? ` → ${decision.shelterLabel || decision.shelterId}`
                    : ''}
                </strong>
                <p>
                  {decision.methodLabel || decision.method || 'Hybrid'}
                  {typeof decision.score === 'number' ? ` · score ${decision.score}` : ''}
                  {typeof decision.load === 'number' ? ` · load ${decision.load}` : ''}
                  {typeof decision.checksPassed === 'number'
                    ? ` · ${decision.checksPassed}/${decision.checksTotal ?? 8} checks passed`
                    : ''}
                </p>
                {passedOver && <p className="why-rejected">{passedOver}</p>}
                {Array.isArray(decision.checks) && decision.checks.length > 0 && (
                  <div className="check-grid compact">
                    {decision.checks.map((c) => (
                      <div
                        key={c.label}
                        className={`check-item ${c.passed ? 'ok' : 'bad'}`}
                      >
                        {c.passed ? '✓' : '✗'} {c.label}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {!cleared && (
              <div className="crew-block">
                <small>CREW / CONTROL</small>
                <div className="incident-actions">
                  <button
                    type="button"
                    onClick={() => crew(
                      { reinforcement: true, note: 'More people on site than first reported' },
                      `Crew: +8 people at ${selected.label || selected.id}. Press Run if it is paused — leftover people get the next free unit.`,
                    )}
                  >
                    More people here
                  </button>
                  <button
                    type="button"
                    onClick={() => crew(
                      { requestedMode: 'water', note: 'Need a boat — road approach gone' },
                      `Crew requested a boat for ${selected.label || selected.id}. Run will prefer a rescue boat.`,
                    )}
                  >
                    Need a boat
                  </button>
                  <button
                    type="button"
                    onClick={() => crew(
                      { roadStatus: 'BLOCKED', note: 'Road blocked near pickup' },
                      'Road closed on the graph — buses will not use that edge.',
                    )}
                  >
                    Road blocked
                  </button>
                  <button
                    className="stand-down"
                    type="button"
                    onClick={() => crew(
                      { standDown: true, note: 'Site already clear — stand down' },
                      'Recall sent — site clear. En-route units stop unless people are already aboard.',
                    )}
                  >
                    Site clear
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
