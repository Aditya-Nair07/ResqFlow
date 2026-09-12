import type { Snapshot } from './api';
import { AlertTriangle, Droplets, Phone } from 'lucide-react';

function shortTime(iso?: string) {
  if (!iso) return '';
  return String(iso).slice(11, 19);
}

export default function PublicReports({ snap }: { snap: Snapshot }) {
  const reports = [...(snap.reports || [])]
    .filter((r) => r.source === 'CITIZEN')
    .sort((a, b) => (b.createdTick || 0) - (a.createdTick || 0))
    .slice(0, 8);

  if (reports.length === 0) {
    return (
      <div className="public-reports panel">
        <div className="panel-heading">
          <div>
            <p className="eyebrow">PUBLIC REPORTS</p>
            <h2>Live citizen reports</h2>
          </div>
          <span className="empty-tag">No reports yet</span>
        </div>
        <p className="public-reports-empty">
          Reports submitted from <b>Public report</b> tab will appear here and on the map.
        </p>
      </div>
    );
  }

  return (
    <div className="public-reports panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">PUBLIC REPORTS</p>
          <h2>Live citizen reports</h2>
        </div>
        <span className="count-badge">{reports.length}</span>
      </div>
      <div className="public-reports-list">
        {reports.map((r) => {
          const isRescue = (r.people || 0) > 0;
          return (
            <div key={r.id} className={`public-report-row ${isRescue ? 'rescue' : 'flood'}`}>
              <div className="public-report-icon">
                {isRescue ? <Phone size={16} /> : <Droplets size={16} />}
              </div>
              <div className="public-report-body">
                <strong>
                  {isRescue ? `Rescue: ${r.people} people` : `Waterlogging (~${Math.round(r.depthCm || 0)} cm)`}
                </strong>
                <small>
                  {r.landmark || r.area || `cell (${Math.round(r.x)},${Math.round(r.y)})`}
                  {r.description ? ` · ${String(r.description).slice(0, 60)}` : ''}
                </small>
                <div className="public-report-meta">
                  <span>{r.id}</span>
                  <span>tick {r.createdTick ?? 0}</span>
                  <span>{shortTime(r.createdAt)}</span>
                  {r.groupId ? <span className="tag mint">→ {r.groupId}</span> : <span className="tag amber">flood only</span>}
                  {r.status === 'DUPLICATE' ? <span className="tag muted">duplicate</span> : null}
                </div>
                {(r.effects?.roadsForcedClosed || []).length > 0 && (
                  <div className="public-report-effect">
                    <AlertTriangle size={12} /> roads closed: {(r.effects.roadsForcedClosed || []).join(', ')}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
