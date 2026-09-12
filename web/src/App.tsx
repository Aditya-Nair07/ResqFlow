import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CirclePause, CirclePlay, RotateCcw, Waves } from 'lucide-react';
import { api, type Snapshot } from './api';
import OpsDesk from './OpsDesk';
import PublicSafety from './PublicSafety';
import PublicReports from './PublicReports';
import FloodMap from './FloodMap';

const DEFAULT_SCENARIO = 'chennai_2015_review';

export default function App() {
  const [publicMode, setPublicMode] = useState(false);
  const [scenarioId, setScenarioId] = useState(DEFAULT_SCENARIO);
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState('');
  const [message, setMessage] = useState('');
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.snapshot(scenarioId);
      setSnap(data);
      if (!selectedGroupId && data.groups?.[0]?.id) setSelectedGroupId(data.groups[0].id);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [scenarioId, selectedGroupId]);

  useEffect(() => {
    setRunning(false);
    setSelectedGroupId(null);
    api
      .reset(scenarioId)
      .then((r) => setSnap(r.snapshot || r))
      .then(() => refresh())
      .catch((err) => setError(String(err)));
  }, [scenarioId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!running) return;
    const timer = window.setInterval(async () => {
      try {
        const result = await api.step({
          scenarioId,
          steps: 1,
          running: true,
          rankingMethod: 'hybrid',
          closedLoop: true,
        });
        setSnap(result.snapshot);
      } catch (err) {
        setRunning(false);
        setError(String(err));
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [running, scenarioId]);

  useEffect(() => {
    const timer = window.setInterval(() => {
      refresh().catch(() => undefined);
    }, 2500);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const metrics = useMemo(() => {
    if (!snap) return { evacuated: 0, waiting: 0, stranded: 0, depth: 0 };
    const waiting = snap.groups
      .filter((g) => !['evacuated', 'RESOLVED', 'REJECTED'].includes(g.status))
      .reduce((sum, g) => sum + Math.max(0, (g.people || 0) - (g.evacuatedPeople || 0)), 0);
    return {
      evacuated: snap.metrics?.peopleEvacuated || 0,
      waiting,
      stranded: snap.groups.filter((g) => String(g.status).toLowerCase().includes('strand')).length,
      depth: snap.flood?.maxDepthCm || 0,
    };
  }, [snap]);

  if (publicMode) {
    return (
      <PublicSafety
        scenarioId={scenarioId}
        snap={snap}
        onSwitchOps={() => setPublicMode(false)}
        onSubmitted={async (groupId?: string) => {
          if (groupId) setSelectedGroupId(groupId);
          await refresh();
          setMessage(
            groupId
              ? `New rescue request ${groupId} is on the map. Press Run — a free unit will be assigned automatically.`
              : 'New public report received — visible on the map and in Public reports panel.',
          );
          setPublicMode(false);
        }}
      />
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-mark"><Waves size={20} /></div>
          <div>
            <strong>ResQFlow<span>-Flood</span></strong>
            <small>FLOOD EVACUATION DESK</small>
          </div>
        </div>
        <div className="mode-switch">
          <button className="active" type="button">Operations</button>
          <button type="button" onClick={() => setPublicMode(true)}>Public report</button>
        </div>
        <div className="scenario">
          <span>SCENARIO</span>
          <select value={scenarioId} onChange={(e) => setScenarioId(e.target.value)}>
            <option value="chennai_2015_review">Chennai flood</option>
            <option value="urban_flood_default">Urban flood</option>
          </select>
        </div>
      </header>

      <div className="disclaimer">
        <AlertTriangle size={14} /> Decision-support demo — not connected to live emergency services.
      </div>

      <main className="main-content review-ops">
        <div className="hero-row review-hero">
          <div>
            <p className="eyebrow">TICK {snap?.tick ?? 0}</p>
            <h1>Move people before <i>the water does.</i></h1>
          </div>
          <div className="hero-actions">
            <button className={`button ${running ? 'pause' : 'primary'}`} type="button" onClick={() => setRunning((v) => !v)}>
              {running ? <CirclePause size={18} /> : <CirclePlay size={18} />} {running ? 'Pause' : 'Run'}
            </button>
            <button
              className="icon-button"
              type="button"
              title="Reset"
              onClick={async () => {
                setRunning(false);
                const r = await api.reset(scenarioId);
                setSnap(r.snapshot || r);
                setMessage('');
              }}
            >
              <RotateCcw size={18} />
            </button>
          </div>
        </div>

        {error && (
          <div className="alert-banner">
            <AlertTriangle size={18} />
            <div><b>API error</b><span>{error}</span></div>
          </div>
        )}
        {message && (
          <div className="desk-message">
            {message}
            <button type="button" onClick={() => setMessage('')}>×</button>
          </div>
        )}

        <div className="stats-grid review-stats">
          <div className="stat-card mint"><div><small>People rescued</small><strong>{metrics.evacuated}</strong></div></div>
          <div className="stat-card yellow"><div><small>Still waiting</small><strong>{metrics.waiting}</strong></div></div>
          <div className="stat-card coral"><div><small>Water depth (cm)</small><strong>{metrics.depth.toFixed(0)}</strong></div></div>
          <div className="stat-card pink"><div><small>Stranded</small><strong>{metrics.stranded}</strong></div></div>
        </div>

        {snap && (
          <div className="workspace-grid review-workspace">
            <div className="left-column">
              <FloodMap snap={snap} />
              <PublicReports snap={snap} />
            </div>
            <aside className="right-column">
              <OpsDesk
                snap={snap}
                scenarioId={scenarioId}
                selectedId={selectedGroupId}
                onSelect={setSelectedGroupId}
                onChange={async (msg) => {
                  setMessage(msg);
                  await refresh();
                }}
              />
              <div className="panel">
                <div className="panel-heading">
                  <div>
                    <p className="eyebrow">SHELTERS</p>
                    <h2>Safe places</h2>
                  </div>
                </div>
                {snap.shelters.map((s) => (
                  <div className="shelter-row" key={s.id}>
                    <div className="shelter-info">
                      <strong>{s.label || s.id}</strong>
                      <small>{s.open === false ? 'Closed' : 'Open'}</small>
                    </div>
                    <div className="capacity">
                      <b>{s.occupancy}/{s.capacity}</b>
                    </div>
                  </div>
                ))}
              </div>
            </aside>
          </div>
        )}
      </main>
    </div>
  );
}
