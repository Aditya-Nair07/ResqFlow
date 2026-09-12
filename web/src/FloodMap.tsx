import { useEffect, useRef, useState } from 'react';
import type { Snapshot } from './api';

/** Spaced flood plant — markers fan out so units and groups do not stack. */

function vehicleShort(type: string, mode?: string) {
  const t = String(type || '').toLowerCase();
  if (mode === 'water' || t.includes('boat')) return 'BOA';
  if (t.includes('truck') || t.includes('high')) return 'TRK';
  if (t.includes('bus')) return 'BUS';
  return String(type || 'UNT').slice(0, 3).toUpperCase();
}

function vehicleColor(type: string, mode?: string) {
  const short = vehicleShort(type, mode);
  if (short === 'BOA') return '#22c55e';
  if (short === 'TRK') return '#a78bfa';
  return '#38bdf8';
}

type Pt = { x: number; y: number };

function fanOut(points: Pt[], minSep: number): Pt[] {
  const out = points.map((p) => ({ ...p }));
  const buckets = new Map<string, number[]>();
  out.forEach((p, i) => {
    const key = `${Math.round(p.x / 14)}_${Math.round(p.y / 14)}`;
    const list = buckets.get(key) || [];
    list.push(i);
    buckets.set(key, list);
  });
  for (const idxs of buckets.values()) {
    if (idxs.length < 2) continue;
    const radius = minSep + (idxs.length - 2) * 6;
    idxs.forEach((i, n) => {
      const angle = -Math.PI / 2 + (n * 2 * Math.PI) / idxs.length;
      out[i].x += Math.cos(angle) * radius;
      out[i].y += Math.sin(angle) * radius;
    });
  }
  return out;
}

function nudgeFrom(point: Pt, others: Pt[], gap: number): Pt {
  let { x, y } = point;
  for (const o of others) {
    const dx = x - o.x;
    const dy = y - o.y;
    const d = Math.hypot(dx, dy);
    if (d < gap && d > 0.1) {
      const s = (gap - d) / d;
      x += dx * s;
      y += dy * s;
    } else if (d <= 0.1) {
      x += gap;
    }
  }
  return { x, y };
}

export default function FloodMap({ snap }: { snap: Snapshot }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wrapRef = useRef<HTMLDivElement | null>(null);
  const [size, setSize] = useState({ w: 720, h: 560 });

  useEffect(() => {
    const wrap = wrapRef.current;
    if (!wrap) return;
    const update = () => {
      const cssW = Math.max(360, wrap.clientWidth);
      const cssH = Math.max(480, Math.min(640, Math.round(cssW * 0.82)));
      setSize({ w: cssW, h: cssH });
    };
    update();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(update) : null;
    ro?.observe(wrap);
    window.addEventListener('resize', update);
    return () => {
      ro?.disconnect();
      window.removeEventListener('resize', update);
    };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || !snap) return;
    const dpr = window.devicePixelRatio || 1;
    const { w: cssW, h: cssH } = size;
    canvas.style.width = `${cssW}px`;
    canvas.style.height = `${cssH}px`;
    canvas.width = Math.floor(cssW * dpr);
    canvas.height = Math.floor(cssH * dpr);
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const gs = snap.flood?.gridSize || 25;
    const pad = 56;
    const usable = Math.min(cssW - pad * 2, cssH - pad * 2);
    const ox = (cssW - usable) / 2;
    const oy = (cssH - usable) / 2 - 6;
    const toCanvas = (x: number, y: number) => ({
      x: ox + (x / Math.max(1, gs - 1)) * usable,
      y: oy + (y / Math.max(1, gs - 1)) * usable,
    });
    const rScale = usable / gs;

    ctx.clearRect(0, 0, cssW, cssH);
    ctx.fillStyle = '#020617';
    ctx.fillRect(0, 0, cssW, cssH);

    const depthField = snap.flood?.depthCm || [];
    for (let y = 0; y < gs; y += 1) {
      for (let x = 0; x < gs; x += 1) {
        const d = depthField[y]?.[x] || 0;
        if (d < 8) continue;
        const p = toCanvas(x, y);
        const alpha = Math.min(0.48, 0.08 + d / 110);
        ctx.fillStyle = d >= 45 ? `rgba(225,29,72,${alpha * 0.75})` : `rgba(14,116,178,${alpha})`;
        ctx.fillRect(p.x - rScale / 2, p.y - rScale / 2, rScale + 0.5, rScale + 0.5);
      }
    }

    ctx.strokeStyle = 'rgba(51,65,85,0.28)';
    ctx.lineWidth = 1;
    for (let i = 0; i <= 3; i += 1) {
      const t = i / 3;
      const x = ox + usable * t;
      const y = oy + usable * t;
      ctx.beginPath();
      ctx.moveTo(x, oy);
      ctx.lineTo(x, oy + usable);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(ox, y);
      ctx.lineTo(ox + usable, y);
      ctx.stroke();
    }

    const closed = new Set(snap.closedEdgeIds || []);
    for (const st of snap.roadEdgeStates || []) {
      if (st?.forcedClosed && st.id) closed.add(st.id);
    }
    for (const edge of snap.roadEdges || []) {
      const from = edge.from || edge.a;
      const to = edge.to || edge.b;
      if (!from || !to) continue;
      const a = toCanvas(from[0], from[1]);
      const b = toCanvas(to[0], to[1]);
      const shut = closed.has(edge.id);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = shut ? 'rgba(239,68,68,0.85)' : 'rgba(148,163,184,0.45)';
      ctx.lineWidth = shut ? 2.4 : 1.8;
      ctx.stroke();
    }
    for (const edge of snap.boatLinks || []) {
      if (!edge.from || !edge.to) continue;
      const a = toCanvas(edge.from[0], edge.from[1]);
      const b = toCanvas(edge.to[0], edge.to[1]);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.setLineDash([5, 5]);
      ctx.strokeStyle = 'rgba(34,197,94,0.4)';
      ctx.lineWidth = 1.4;
      ctx.stroke();
      ctx.setLineDash([]);
    }

    const liveGroups = (snap.groups || []).filter(
      (g) => !['evacuated', 'RESOLVED', 'REJECTED'].includes(g.status),
    );
    const groupBase = liveGroups.map((g) => toCanvas(g.x, g.y));
    const groupPts = fanOut(groupBase, 22);

    const vehicles = snap.vehicles || [];
    const vehBase = vehicles.map((v) => toCanvas(v.x, v.y));
    const vehPts = fanOut(vehBase, 24).map((p) => nudgeFrom(p, groupPts, 26));

    for (const v of vehicles) {
      if (v.status !== 'busy') continue;
      const group = liveGroups.find((g) => g.id === v.assignedGroupId);
      const shelter = (snap.shelters || []).find((s) => s.id === (v.targetShelterId || group?.assignedShelterId));
      const vi = vehicles.indexOf(v);
      const start = vehPts[vi];
      ctx.beginPath();
      ctx.moveTo(start.x, start.y);
      if (v.phase === 'to_shelter' && shelter) {
        const end = toCanvas(shelter.x, shelter.y);
        ctx.lineTo(end.x, end.y);
      } else if (group) {
        const gi = liveGroups.indexOf(group);
        const mid = groupPts[gi] || toCanvas(group.x, group.y);
        ctx.lineTo(mid.x, mid.y);
      }
      ctx.strokeStyle = 'rgba(226, 232, 240, 0.4)';
      ctx.lineWidth = 1.6;
      ctx.setLineDash([7, 6]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    for (const d of snap.depots || []) {
      const p = toCanvas(d.x, d.y);
      ctx.fillStyle = 'rgba(34, 197, 94, 0.16)';
      ctx.strokeStyle = '#22c55e';
      ctx.lineWidth = 1.6;
      ctx.fillRect(p.x - 9, p.y - 9, 18, 18);
      ctx.strokeRect(p.x - 9, p.y - 9, 18, 18);
      ctx.fillStyle = '#86efac';
      ctx.font = '600 10px sans-serif';
      const label = String(d.label || 'Depot').replace(/ Depot$/i, '');
      ctx.fillText(label, p.x + 13, p.y + 3);
    }

    for (const s of snap.shelters || []) {
      const p = toCanvas(s.x, s.y);
      const full = s.open === false || s.occupancy >= s.capacity;
      ctx.fillStyle = full ? 'rgba(239,68,68,0.16)' : 'rgba(34, 197, 94, 0.16)';
      ctx.strokeStyle = full ? '#ef4444' : '#22c55e';
      ctx.lineWidth = 1.6;
      ctx.fillRect(p.x - 9, p.y - 9, 18, 18);
      ctx.strokeRect(p.x - 9, p.y - 9, 18, 18);
      ctx.fillStyle = full ? '#fecaca' : '#bbf7d0';
      ctx.font = '600 10px sans-serif';
      const name = String(s.label || s.id).split(' ')[0];
      ctx.fillText(name, p.x + 13, p.y);
      ctx.fillStyle = '#94a3b8';
      ctx.font = '10px sans-serif';
      ctx.fillText(`${s.occupancy}/${s.capacity}`, p.x + 13, p.y + 12);
    }

    liveGroups.forEach((g, i) => {
      const p = groupPts[i];
      const critical = g.severity === 'CRITICAL' || (g.vulnerability || 0) >= 90;
      const stranded = String(g.status).toLowerCase().includes('strand');
      ctx.beginPath();
      ctx.moveTo(p.x, p.y - 11);
      ctx.lineTo(p.x - 10, p.y + 9);
      ctx.lineTo(p.x + 10, p.y + 9);
      ctx.closePath();
      ctx.fillStyle = stranded ? '#475569' : critical ? '#ef4444' : '#f59e0b';
      ctx.fill();
      ctx.strokeStyle = '#fff7ed';
      ctx.lineWidth = 1.4;
      ctx.stroke();
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 10px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(String(g.people || 0), p.x, p.y + 5);
      ctx.textAlign = 'left';
    });

    vehicles.forEach((v, i) => {
      const p = vehPts[i];
      const short = vehicleShort(v.type, v.mode);
      const idle = v.status === 'available';
      ctx.beginPath();
      ctx.arc(p.x, p.y, 10, 0, Math.PI * 2);
      ctx.fillStyle = idle ? vehicleColor(v.type, v.mode) : '#f59e0b';
      ctx.fill();
      ctx.lineWidth = 1.6;
      ctx.strokeStyle = '#eaf7ff';
      ctx.stroke();
      ctx.fillStyle = '#08111f';
      ctx.font = 'bold 8px sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText(short, p.x, p.y + 3);
      const phase = String(v.phase || '');
      const phaseLabel =
        phase === 'to_pickup' ? 'pickup' : phase === 'to_shelter' ? 'shelter' : phase === 'loading' ? 'load' : '';
      if (phaseLabel) {
        ctx.fillStyle = '#fde68a';
        ctx.font = '600 9px sans-serif';
        ctx.fillText(phaseLabel, p.x, p.y - 14);
      }
      ctx.textAlign = 'left';
    });

    ctx.fillStyle = '#64748b';
    ctx.font = '11px sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(
      `Tick ${snap.tick || 0} · peak ${Math.round(snap.flood?.maxDepthCm || 0)} cm`,
      14,
      cssH - 12,
    );
  }, [snap, size]);

  const method = (snap.rankingMethod || 'hybrid').replace(/^./, (c) => c.toUpperCase());
  const closedLoop = snap.closedLoop !== false;

  return (
    <div className="map-panel panel plant-panel">
      <div className="panel-heading plant-heading">
        <div>
          <p className="eyebrow">PHYSICAL PLANT (SIMULATED)</p>
          <h2>Flood evacuation graph</h2>
        </div>
        <div className="plant-badges">
          <span className="plant-badge blue">Flood-GAPD</span>
          <span className="plant-badge cyan">{method}</span>
          <span className={`plant-badge ${closedLoop ? 'green' : 'amber'}`}>
            {closedLoop ? 'Closed loop' : 'Open loop'}
          </span>
        </div>
      </div>
      <div className="map-wrap plant-map-wrap" ref={wrapRef}>
        <canvas ref={canvasRef} className="plant-map-canvas" />
      </div>
      <div className="plant-legend">
        <span><i className="lg base" /> Depot / shelter</span>
        <span><i className="lg route" /> Road / route</span>
        <span><i className="lg avail" /> Available unit</span>
        <span><i className="lg assigned" /> Assigned unit</span>
        <span><i className="lg critical" /> People needing help</span>
      </div>
    </div>
  );
}
