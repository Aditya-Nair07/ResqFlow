import { api, type Snapshot } from './api';
import { resourceNeed } from './resourceNeed';

function rankLabel(method?: string) {
  switch ((method || 'hybrid').toLowerCase()) {
    case 'weighted':
      return 'Weighted';
    case 'ellipse':
      return 'Ellipse';
    case 'polygon':
      return 'Polygon';
    default:
      return 'Hybrid (Weighted + Ellipse + Polygon)';
  }
}

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
              <small>{g.people} people · {statusLabel(g.status)}</small>
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
                <p className="core-logic">
                  Decision core: Flood-GAPD priority ·{' '}
                  {rankLabel(snap.rankingMethod)} scoring · 8-check verified
                  {typeof selected.gapdScore === 'number'
                    ? ` · GAPD ${selected.gapdScore}`
                    : ''}
                </p>
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
