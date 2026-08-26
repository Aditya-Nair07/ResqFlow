import { api, type Snapshot } from './api';

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
  const trace = snap.recentTraces.find((t) => t.groupId === selected?.id);

  return (
    <div className="incident-desk">
      <div className="desk-heading">
        <div>
          <p className="eyebrow">OPERATIONS</p>
          <h2>Incident response queue</h2>
          <span>Flood-GAPD · trust · eight-check verification from backend · includes seeded Chennai reports</span>
        </div>
      </div>
      <div className="incident-layout">
        <div className="incident-queue">
          <div className="queue-heading"><span>QUEUE</span><span>{snap.groups.length}</span></div>
          {snap.groups.map((g) => (
            <button
              key={g.id}
              type="button"
              className={`incident-card ${selected?.id === g.id ? 'selected' : ''}`}
              onClick={() => onSelect(g.id)}
            >
              <div className="incident-card-top">
                <span>{g.id}</span>
                <b className={`severity ${(g.severity || 'MEDIUM').toLowerCase()}`}>{g.severity || g.status}</b>
              </div>
              <b>{g.label || g.area || g.id}</b>
              <small>{g.people} people · trust {g.trust ?? '—'} · {g.source || 'SIMULATOR'}</small>
              <div className="incident-card-bottom">
                <strong>{g.status}</strong>
                <span>GAPD {g.gapdScore ?? '—'}</span>
              </div>
            </button>
          ))}
        </div>
        {selected && (
          <div className="incident-detail">
            <div className="detail-heading">
              <div>
                <small>{selected.id}</small>
                <h3>{selected.label || selected.id}</h3>
                <p>{selected.description || selected.area || selected.landmark || 'Evacuation group'}</p>
              </div>
              <div className="status-pill">{selected.status}</div>
            </div>
            <div className="detail-grid">
              <div><small>PEOPLE</small><p>{selected.people}</p></div>
              <div><small>VULNERABILITY</small><p>{selected.vulnerability}</p></div>
              <div><small>TRUST / CONFIDENCE</small><p>{selected.trust ?? '—'} / {selected.confidenceScore ?? '—'}</p></div>
              <div><small>DEADLINE TICK</small><p>{selected.deadlineTick}</p></div>
              <div><small>GAPD BAND / SCORE</small><p>{selected.gapdBand ?? '—'} / {selected.gapdScore ?? '—'}</p></div>
              <div><small>ASSIGNED</small><p>{selected.assignedVehicleId || '—'} → {selected.assignedShelterId || '—'}</p></div>
            </div>
            {(selected.severityReasons || []).length > 0 && (
              <div className="severity-reasons">{(selected.severityReasons || []).join(' · ')}</div>
            )}
            {trace?.verification?.checks && (
              <div className="check-grid">
                {trace.verification.checks.map((c: any) => (
                  <div key={c.label} className={`check-item ${c.passed ? 'ok' : 'bad'}`}>
                    {c.passed ? '✓' : '✗'} {c.label}
                  </div>
                ))}
              </div>
            )}
            <div className="incident-actions">
              <button
                type="button"
                onClick={async () => {
                  await api.verify(selected.id, { scenarioId, accept: true, actor: 'operator' });
                  await onChange(`Verified ${selected.id}`);
                }}
              >
                Verify
              </button>
              <button
                type="button"
                onClick={async () => {
                  await api.prioritize(selected.id, { scenarioId, actor: 'operator' });
                  await onChange(`Prioritized ${selected.id} into Flood-GAPD queue`);
                }}
              >
                Prioritize
              </button>
              <button
                type="button"
                onClick={async () => {
                  await api.operatorUpdate({
                    scenarioId,
                    groupId: selected.id,
                    roadStatus: 'BLOCKED',
                    actor: 'field_team',
                    source: 'FIELD_TEAM',
                    note: 'Road blocked near pickup',
                  });
                  await onChange(`Quick field: road blocked for ${selected.id}`);
                }}
              >
                Quick: road blocked
              </button>
            </div>
            <div className="audit">
              <div className="audit-title"><b>Audit</b></div>
              {(selected.audit || []).slice(-8).map((a: any, i: number) => (
                <div className="audit-row" key={`${a.at}-${i}`}>
                  <time>{String(a.at).slice(11, 19)}</time>
                  <div><b>{a.action}</b>{a.detail}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
