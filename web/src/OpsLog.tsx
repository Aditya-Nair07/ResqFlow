import type { Snapshot } from './api';
import { buildEventFeed } from './formatOpsLog';

/** Slim control-room log under the map. */
export default function OpsLog({ snap }: { snap: Snapshot }) {
  const rows = buildEventFeed(snap.events, 8);

  return (
    <div className="ops-log panel">
      <div className="panel-heading ops-log-heading">
        <div>
          <p className="eyebrow">OPS LOG</p>
          <h2>Live events</h2>
        </div>
        <span className="ops-log-meta">tick {snap.tick}</span>
      </div>
      {rows.length === 0 ? (
        <p className="ops-log-empty">Quiet for now — Run the plant or send a public report.</p>
      ) : (
        <ul className="ops-log-list">
          {rows.map((row) => (
            <li key={row.key} className={`ops-log-row tone-${row.tone}`}>
              <span className="ops-log-tick">t{row.tick}</span>
              <span className={`ops-log-tag ${row.tone}`}>{row.tag}</span>
              <span className="ops-log-text">{row.text}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
