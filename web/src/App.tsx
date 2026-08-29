import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CirclePause, CirclePlay, RotateCcw, Waves } from 'lucide-react';
import { api, type Snapshot } from './api';
import OpsDesk from './OpsDesk';
import PublicSafety from './PublicSafety';
import PlannerPanel from './PlannerPanel';
import FloodMap from './FloodMap';

const DEFAULT_SCENARIO = 'chennai_2015_review';

export default function App() {
  const [publicMode, setPublicMode] = useState(false);
  const [scenarioId, setScenarioId] = useState(DEFAULT_SCENARIO);
  const [difficulty, setDifficulty] = useState<'normal' | 'heavy' | 'crisis'>('normal');
  const [snap, setSnap] = useState<Snapshot | null>(null);
  const [running, setRunning] = useState(false);
  const [rankingMethod, setRankingMethod] = useState('hybrid');
  const [error, setError] = useState('');
  const [message, setMessage] = useState('Chennai 2015 review plant connected to FastAPI.');
  const [plans, setPlans] = useState<any>(null);
  const [eventAfter, setEventAfter] = useState(0);
  const [liveEvents, setLiveEvents] = useState<any[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(null);
  const [fixtureMeta, setFixtureMeta] = useState<any>(null);

  const refresh = useCallback(async () => {
    try {
      const data = await api.snapshot(scenarioId);
      setSnap(data);
      setRankingMethod(data.rankingMethod || 'hybrid');
      if (data.fixtureMeta) setFixtureMeta(data.fixtureMeta);
      if (!selectedGroupId && data.groups?.[0]?.id) setSelectedGroupId(data.groups[0].id);
      setError('');
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [scenarioId, selectedGroupId]);

  useEffect(() => {
    api.chennaiFixtures().then((f) => setFixtureMeta(f.meta)).catch(() => undefined);
  }, []);

  useEffect(() => {
    setRunning(false);
    setPlans(null);
    setLiveEvents([]);
    setEventAfter(0);
    setSelectedGroupId(null);
    api
      .reset(scenarioId, difficulty)
      .then((r) => {
        setSnap(r.snapshot || r);
        setMessage(`Loaded ${scenarioId} · difficulty ${difficulty}`);
      })
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
          rankingMethod,
          closedLoop: true,
          difficulty,
        });
        setSnap(result.snapshot);
      } catch (err) {
        setRunning(false);
        setError(String(err));
      }
    }, 1200);
    return () => window.clearInterval(timer);
  }, [running, scenarioId, rankingMethod, difficulty]);

  useEffect(() => {
    const timer = window.setInterval(async () => {
      try {
        const data = await api.events(scenarioId, eventAfter);
        if (data.events?.length) {
          setLiveEvents((prev) => [...data.events, ...prev].slice(0, 40));
          setEventAfter(data.eventSeq);
          await refresh();
        }
      } catch {
        /* polling fallback */
      }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [scenarioId, eventAfter, refresh]);

  const metrics = useMemo(() => {
    if (!snap) return { evacuated: 0, stranded: 0, active: 0, depth: 0 };
    return {
      evacuated: snap.metrics?.peopleEvacuated || 0,
      stranded: snap.groups.filter((g) => String(g.status).toLowerCase().includes('strand')).length,
      active: snap.vehicles.filter((v) => v.status === 'busy').length,
      depth: snap.flood?.maxDepthCm || 0,
    };
  }, [snap]);

  const meta = snap?.fixtureMeta || fixtureMeta;

  async function onMessage(msg: string) {
    setMessage(msg);
    await refresh();
  }

  if (publicMode) {
    return (
      <PublicSafety
        scenarioId={scenarioId}
        snap={snap}
        onSwitchOps={() => setPublicMode(false)}
        onSubmitted={async () => {
          await refresh();
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
            <small>UNIFIED DECISION SUPPORT</small>
          </div>
        </div>
        <div className="mode-switch">
          <button className="active" type="button">Operations Desk</button>
          <button type="button" onClick={() => setPublicMode(true)}>Public Safety View</button>
        </div>
        <div className="scenario">
          <span>SCENARIO</span>
          <select value={scenarioId} onChange={(e) => setScenarioId(e.target.value)}>
            <option value="chennai_2015_review">Chennai 2015 Flood</option>
            <option value="urban_flood_default">Urban flood default</option>
            <option value="urban_flood_stress">Stress</option>
            <option value="urban_flood_boat_only">Boat only</option>
          </select>
        </div>
        <div className="top-controls">
          <label className={`difficulty ${difficulty}`}>
            <span>DIFFICULTY</span>
            <select
              value={difficulty}
              onChange={async (e) => {
                const next = e.target.value as typeof difficulty;
                setDifficulty(next);
                setRunning(false);
                const r = await api.reset(scenarioId, next);
                setSnap(r.snapshot || r);
                setPlans(null);
                setLiveEvents([]);
                setEventAfter(0);
                setMessage(`Difficulty → ${next} (rainfall + shelter stress applied on plant)`);
              }}
            >
              <option value="normal">Normal</option>
              <option value="heavy">Heavy Rain</option>
              <option value="crisis">Crisis</option>
            </select>
          </label>
        </div>
      </header>

      <div className="disclaimer">
        <AlertTriangle size={14} /> DECISION SUPPORT PROTOTYPE — FastAPI is authoritative. Chennai fixtures are demonstration data, not live emergency feeds.
      </div>

      <main className="main-content">
        <div className="hero-row">
          <div>
            <p className="eyebrow">LIVE PLANT / TICK {snap?.tick ?? 0} · {difficulty.toUpperCase()}</p>
            <h1>Move people before<br /><i>the water does.</i></h1>
          </div>
          <div className="hero-actions">
            <button className={`button ${running ? 'pause' : 'primary'}`} type="button" onClick={() => setRunning((v) => !v)}>
              {running ? <CirclePause size={18} /> : <CirclePlay size={18} />} {running ? 'Pause' : 'Run rehearsal'}
            </button>
            <button
              className="icon-button"
              type="button"
              title="Reset"
              onClick={async () => {
                setRunning(false);
                const r = await api.reset(scenarioId, difficulty);
                setSnap(r.snapshot || r);
                setPlans(null);
                setLiveEvents([]);
                setEventAfter(0);
                setMessage('Session reset with Chennai fixtures / difficulty.');
              }}
            >
              <RotateCcw size={18} />
            </button>
          </div>
        </div>

        {meta && (
          <div className="chennai-data-strip">
            <div>
              <b>{meta.label || 'CHENNAI 2015 FLOOD DATA'}</b>
              <span>{meta.note || 'Demonstration fixtures from data/chennai'}</span>
            </div>
            <strong>{meta.shelterCount ?? '—'} shelters</strong>
            <strong>{meta.reportCount ?? '—'} field reports</strong>
            <span className="chennai-areas">{(meta.areas || []).join(' · ')}</span>
          </div>
        )}

        <div className="ops-toolbar">
          <label>
            Ranking method{' '}
            <select value={rankingMethod} onChange={(e) => setRankingMethod(e.target.value)}>
              <option value="hybrid">Hybrid</option>
              <option value="weighted">Weighted</option>
              <option value="ellipse">Ellipse</option>
              <option value="polygon">Polygon</option>
            </select>
          </label>
          <button
            className="primary"
            type="button"
            onClick={async () => {
              const result = await api.comparePlans({ scenarioId, rankingMethod });
              setPlans(result);
              setMessage(result.explanation || 'Plans compared.');
            }}
          >
            Compare plans
          </button>
          <button
            type="button"
            onClick={async () => {
              await api.weather({ scenarioId, applyNudge: true });
              await onMessage('Weather context refreshed (Open-Meteo or offline fixture).');
            }}
          >
            Refresh weather
          </button>
        </div>

        {error && <div className="alert-banner"><AlertTriangle size={18} /><div><b>API error</b><span>{error}</span></div></div>}
        {message && <div className="desk-message">{message}<button type="button" onClick={() => setMessage('')}>×</button></div>}

        <div className="stats-grid">
          <div className="stat-card mint"><div><small>People evacuated</small><strong>{metrics.evacuated}</strong></div></div>
          <div className="stat-card yellow"><div><small>Vehicles active</small><strong>{metrics.active}</strong></div></div>
          <div className="stat-card coral"><div><small>Peak depth cm</small><strong>{metrics.depth.toFixed(0)}</strong><span>rain {snap?.rainfallPerTick?.toFixed?.(2) ?? '—'}/tick</span></div></div>
          <div className="stat-card pink"><div><small>Stranded</small><strong>{metrics.stranded}</strong></div></div>
        </div>

        {snap && (
          <OpsDesk
            snap={snap}
            scenarioId={scenarioId}
            selectedId={selectedGroupId}
            onSelect={setSelectedGroupId}
            onChange={onMessage}
          />
        )}

        {snap && (
          <PlannerPanel
            plans={plans}
            scenarioId={scenarioId}
            tick={snap.tick}
            snap={snap}
            selectedGroupId={selectedGroupId}
            rankingMethod={rankingMethod}
            onMessage={onMessage}
            onPlans={setPlans}
            onSelectGroup={setSelectedGroupId}
          />
        )}

        {snap && (
          <div className="workspace-grid">
            <FloodMap snap={snap} difficulty={difficulty} />
            <aside className="right-column">
              <div className="panel">
                <div className="panel-heading"><div><p className="eyebrow">EVENTS</p><h2>Live feed</h2></div></div>
                <div className="event-feed" style={{ padding: '0 16px 16px' }}>
                  {liveEvents.length === 0 && <div>Waiting for sensing / plan events…</div>}
                  {liveEvents.map((ev) => (
                    <div key={ev.seq}>#{ev.seq} t{ev.tick} · {ev.type}</div>
                  ))}
                </div>
              </div>
              <div className="panel">
                <div className="panel-heading"><div><p className="eyebrow">SHELTERS</p><h2>Capacity</h2></div></div>
                {snap.shelters.map((s) => (
                  <div className="shelter-row" key={s.id}>
                    <div className="shelter-info">
                      <strong>{s.label || s.id}</strong>
                      <small>{s.open === false ? 'Closed' : 'Open'} · reserved {s.reservedCapacity || 0}</small>
                    </div>
                    <div className="capacity"><b>{s.occupancy}/{s.capacity}</b></div>
                  </div>
                ))}
              </div>
            </aside>
          </div>
        )}

        <footer>
          Friend Chennai UX + field feedback wired onto the main FastAPI plant (Flood-GAPD, ranking, 8-check, NetworkX). Demonstration data only.
        </footer>
      </main>
    </div>
  );
}
