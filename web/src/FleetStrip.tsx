import type { Snapshot } from './api';

/** Read-only fleet strip — one chip per unit (type · status · task · load). */

function unitKind(type: string, mode?: string): 'boat' | 'truck' | 'bus' | 'unit' {
  const t = String(type || '').toLowerCase();
  if (mode === 'water' || t.includes('boat')) return 'boat';
  if (t.includes('truck') || t.includes('high')) return 'truck';
  if (t.includes('bus')) return 'bus';
  return 'unit';
}

const KIND_TAG: Record<string, string> = { boat: 'BOA', truck: 'TRK', bus: 'BUS', unit: 'UNT' };

const PHASE_LABEL: Record<string, string> = {
  to_pickup: 'to pickup',
  loading: 'loading',
  to_shelter: 'to shelter',
  returning: 'returning',
  idle: 'standby',
};

export default function FleetStrip({ snap }: { snap: Snapshot }) {
  const vehicles = snap.vehicles || [];
  const available = vehicles.filter((v) => v.status === 'available').length;
  const busy = vehicles.length - available;

  return (
    <div className="panel fleet-panel">
      <div className="panel-heading fleet-heading">
        <div>
          <p className="eyebrow">FLEET</p>
          <h2>Units on shift</h2>
        </div>
        <span className="fleet-summary">
          <b className="mint">{available}</b> free · <b className="amber">{busy}</b> tasked · {vehicles.length} total
        </span>
      </div>
      <div className="fleet-strip">
        {vehicles.map((v) => {
          const kind = unitKind(v.type, v.mode);
          const isBusy = v.status === 'busy';
          const group = snap.groups?.find((g) => g.id === v.assignedGroupId);
          const task = isBusy
            ? group
              ? `${group.area || group.label || v.assignedGroupId}`
              : PHASE_LABEL[String(v.phase)] || 'tasked'
            : 'standby';
          return (
            <div className={`fleet-chip kind-${kind} ${isBusy ? 'busy' : 'free'}`} key={v.id}>
              <span className="chip-tag">{KIND_TAG[kind]}</span>
              <div className="chip-body">
                <strong>{v.label || `${v.type} ${v.id}`}</strong>
                <small>{task}</small>
              </div>
              <span className="chip-load">
                {v.load || 0}/{v.capacity || 0}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
