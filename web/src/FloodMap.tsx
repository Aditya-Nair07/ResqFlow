import type { Snapshot } from './api';

export default function FloodMap({
  snap,
  difficulty = 'normal',
}: {
  snap: Snapshot;
  difficulty?: string;
}) {
  const grid = snap.flood?.gridSize || 25;
  const depth = snap.flood?.depthCm || [];
  const cells = [];
  for (let y = 0; y < grid; y += 1) {
    for (let x = 0; x < grid; x += 1) {
      const d = depth[y]?.[x] || 0;
      const alpha = Math.min(0.75, d / 80);
      const color = d > 50 ? `rgba(215,90,75,${alpha})` : `rgba(52,155,185,${alpha})`;
      cells.push(<div className="cell" key={`${x}-${y}`} style={{ backgroundColor: color }} />);
    }
  }

  const pct = (v: number) => `${(v / Math.max(1, grid - 1)) * 100}%`;
  const isChennai = String(snap.scenarioId || '').startsWith('chennai');

  return (
    <div className="map-panel panel">
      <div className="panel-heading">
        <div>
          <p className="eyebrow">LIVE FLOOD MODEL</p>
          <h2>
            {isChennai ? 'Chennai flood map' : 'Plant map'}{' '}
            <span className={`difficulty-badge ${difficulty}`}>{difficulty.toUpperCase()}</span>
          </h2>
        </div>
        <div className="map-legend">
          <span><i className="legend-dot dry" />Safe</span>
          <span><i className="legend-dot wet" />Flooding</span>
          <span><i className="legend-dot critical" />Danger</span>
        </div>
      </div>
      <div className="map-wrap">
        <div
          className="map-grid"
          style={{ gridTemplateColumns: `repeat(${grid}, 1fr)`, gridTemplateRows: `repeat(${grid}, 1fr)` }}
        >
          {cells}
        </div>
        {snap.groups.map((g) => (
          <div
            key={g.id}
            className={`map-marker group-marker ${g.status}`}
            style={{ left: pct(g.x), top: pct(g.y) }}
            title={`${g.id} ${g.status} ${g.area || ''}`}
          >
            {g.people}
          </div>
        ))}
        {snap.shelters.map((s) => (
          <div key={s.id} className="map-marker shelter-marker" style={{ left: pct(s.x), top: pct(s.y) }}>⌂</div>
        ))}
        {snap.vehicles.map((v) => (
          <div
            key={v.id}
            className="vehicle-marker"
            style={{ left: pct(v.x), top: pct(v.y), color: v.mode === 'water' ? '#70d4b7' : '#f7b955' }}
            title={`${v.type} ${v.status}`}
          >
            {String(v.type || 'V')[0]}
          </div>
        ))}
      </div>
      <div className="map-footer">
        <span>Tick {snap.tick} · grid {grid}×{grid}</span>
        <span>Rain {snap.rainfallPerTick?.toFixed?.(2) ?? '—'} / tick</span>
        <b>{(snap.flood?.maxDepthCm || 0) > 50 ? 'CRITICAL WATER LEVELS DETECTED' : 'MONITORING'}</b>
      </div>
    </div>
  );
}
