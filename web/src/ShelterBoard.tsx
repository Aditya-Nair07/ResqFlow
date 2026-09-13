import type { Snapshot } from './api';

/** Read-only shelter board — occupancy bar (used + reserved) and seats left. */

export default function ShelterBoard({ snap }: { snap: Snapshot }) {
  const shelters = snap.shelters || [];
  const totalCap = shelters.reduce((s, x) => s + (x.capacity || 0), 0);
  const totalOcc = shelters.reduce((s, x) => s + (x.occupancy || 0), 0);

  return (
    <div className="panel shelter-board">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">SHELTERS</p>
          <h2>Safe places</h2>
        </div>
        <span className="fleet-summary">
          <b className="mint">{Math.max(0, totalCap - totalOcc)}</b> seats left
        </span>
      </div>
      {shelters.map((s) => {
        const cap = s.capacity || 1;
        const occ = s.occupancy || 0;
        const reserved = s.reservedCapacity || 0;
        const seatsLeft = Math.max(0, cap - occ - reserved);
        const closed = s.open === false;
        const occPct = Math.min(100, (occ / cap) * 100);
        const resPct = Math.min(100 - occPct, (reserved / cap) * 100);
        const tone = closed ? 'closed' : seatsLeft === 0 ? 'full' : occPct >= 80 ? 'tight' : 'open';
        return (
          <div className={`shelter-line tone-${tone}`} key={s.id}>
            <div className="shelter-line-top">
              <strong>{s.label || s.id}</strong>
              <span className="shelter-seats">
                {closed ? 'Closed' : `${seatsLeft} left`}
              </span>
            </div>
            <div className="shelter-bar">
              <i className="occ" style={{ width: `${occPct}%` }} />
              <i className="res" style={{ width: `${resPct}%` }} />
            </div>
            <small>
              {occ}/{cap} sheltered{reserved > 0 ? ` · ${reserved} reserved` : ''}
            </small>
          </div>
        );
      })}
    </div>
  );
}
