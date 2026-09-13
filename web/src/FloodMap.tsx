import { useEffect, useRef, useState } from 'react';
import type { Snapshot } from './api';

/** Control-room flood map — layered water, inked roads, themed unit icons. */

function vehicleShort(type: string, mode?: string) {
  const t = String(type || '').toLowerCase();
  if (mode === 'water' || t.includes('boat')) return 'BOA';
  if (t.includes('truck') || t.includes('high')) return 'TRK';
  if (t.includes('bus')) return 'BUS';
  return String(type || 'UNT').slice(0, 3).toUpperCase();
}

function vehicleColor(type: string, mode?: string) {
  const short = vehicleShort(type, mode);
  if (short === 'BOA') return '#34d399';
  if (short === 'TRK') return '#c4b5fd';
  return '#7dd3fc';
}

type Pt = { x: number; y: number };

function fanOut(points: Pt[], minSep: number): Pt[] {
  const out = points.map((p) => ({ ...p }));
  const buckets = new Map<string, number[]>();
  out.forEach((p, i) => {
    const key = `${Math.round(p.x / 16)}_${Math.round(p.y / 16)}`;
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

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  const rad = Math.min(r, w / 2, h / 2);
  ctx.beginPath();
  ctx.moveTo(x + rad, y);
  ctx.arcTo(x + w, y, x + w, y + h, rad);
  ctx.arcTo(x + w, y + h, x, y + h, rad);
  ctx.arcTo(x, y + h, x, y, rad);
  ctx.arcTo(x, y, x + w, y, rad);
  ctx.closePath();
}

/** Draw a small recognizable vehicle glyph centred at (0,0) on the current transform. */
function drawVehicleGlyph(ctx: CanvasRenderingContext2D, short: string, ink: string) {
  ctx.fillStyle = ink;
  ctx.strokeStyle = ink;
  ctx.lineWidth = 1.1;
  if (short === 'BOA') {
    // hull + sail dot
    ctx.beginPath();
    ctx.moveTo(-6, 1);
    ctx.lineTo(6, 1);
    ctx.lineTo(3.5, 5);
    ctx.lineTo(-3.5, 5);
    ctx.closePath();
    ctx.fill();
    ctx.beginPath();
    ctx.moveTo(0, 1);
    ctx.lineTo(0, -5);
    ctx.lineTo(4, -2);
    ctx.closePath();
    ctx.fill();
  } else if (short === 'TRK') {
    // cargo box + cab
    ctx.fillRect(-6, -3.5, 7, 7);
    ctx.fillRect(1.5, -1, 4.5, 4.5);
  } else if (short === 'BUS') {
    // rounded body + windows
    roundRect(ctx, -6.5, -4, 13, 8, 2);
    ctx.fill();
    ctx.fillStyle = '#0b1a1d';
    ctx.fillRect(-4.5, -2, 2.2, 2.2);
    ctx.fillRect(-1.2, -2, 2.2, 2.2);
    ctx.fillRect(2.1, -2, 2.2, 2.2);
  } else {
    ctx.font = 'bold 8px "DM Mono", monospace';
    ctx.textAlign = 'center';
    ctx.fillText(short, 0, 3);
    ctx.textAlign = 'left';
  }
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
      const cssH = Math.max(500, Math.min(680, Math.round(cssW * 0.84)));
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
    const pad = 40;
    const usable = Math.min(cssW - pad * 2, cssH - pad * 2);
    const ox = (cssW - usable) / 2;
    const oy = (cssH - usable) / 2 - 6;
    const toCanvas = (x: number, y: number) => ({
      x: ox + (x / Math.max(1, gs - 1)) * usable,
      y: oy + (y / Math.max(1, gs - 1)) * usable,
    });
    const cell = usable / gs;

    // --- land base ---
    const grad = ctx.createLinearGradient(0, 0, 0, cssH);
    grad.addColorStop(0, '#0b1b1e');
    grad.addColorStop(1, '#081416');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, cssW, cssH);

    // subtle map frame
    ctx.strokeStyle = 'rgba(112,212,183,0.14)';
    ctx.lineWidth = 1;
    ctx.strokeRect(ox - 14, oy - 14, usable + 28, usable + 28);

    // --- flood field: layered bands (safe → warning → danger) ---
    const depthField = snap.flood?.depthCm || [];
    for (let y = 0; y < gs; y += 1) {
      for (let x = 0; x < gs; x += 1) {
        const d = depthField[y]?.[x] || 0;
        if (d < 6) continue;
        const p = toCanvas(x, y);
        let color: string;
        if (d >= 45) {
          const a = Math.min(0.5, 0.22 + d / 220);
          color = `rgba(224,86,74,${a})`;
        } else if (d >= 25) {
          const a = Math.min(0.46, 0.16 + d / 200);
          color = `rgba(54,124,182,${a})`;
        } else {
          const a = Math.min(0.34, 0.08 + d / 220);
          color = `rgba(72,159,177,${a})`;
        }
        ctx.fillStyle = color;
        ctx.fillRect(p.x - cell / 2, p.y - cell / 2, cell + 0.6, cell + 0.6);
      }
    }

    // --- district hairline grid (every 4 cells) ---
    ctx.strokeStyle = 'rgba(120,170,168,0.06)';
    ctx.lineWidth = 1;
    for (let g = 0; g <= gs; g += 4) {
      const a = toCanvas(g, 0);
      const b = toCanvas(g, gs - 1);
      ctx.beginPath();
      ctx.moveTo(a.x, oy);
      ctx.lineTo(a.x, oy + usable);
      ctx.stroke();
      const c = toCanvas(0, g);
      ctx.beginPath();
      ctx.moveTo(ox, c.y);
      ctx.lineTo(ox + usable, c.y);
      ctx.stroke();
    }

    // --- waterway (soft blue band under boat links) ---
    for (const edge of snap.boatLinks || []) {
      if (!edge.from || !edge.to) continue;
      const a = toCanvas(edge.from[0], edge.from[1]);
      const b = toCanvas(edge.to[0], edge.to[1]);
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = 'rgba(56,150,180,0.28)';
      ctx.lineWidth = 9;
      ctx.lineCap = 'round';
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.setLineDash([3, 7]);
      ctx.strokeStyle = 'rgba(147,220,236,0.5)';
      ctx.lineWidth = 1.3;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.lineCap = 'butt';
    }

    // --- roads: casing + ink stroke ---
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
      // casing
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      ctx.strokeStyle = 'rgba(6,14,15,0.65)';
      ctx.lineWidth = shut ? 5 : 4.5;
      ctx.lineCap = 'round';
      ctx.stroke();
      // surface
      ctx.beginPath();
      ctx.moveTo(a.x, a.y);
      ctx.lineTo(b.x, b.y);
      if (shut) {
        ctx.setLineDash([6, 5]);
        ctx.strokeStyle = 'rgba(232,120,82,0.95)';
        ctx.lineWidth = 2.4;
      } else {
        ctx.strokeStyle = 'rgba(176,196,190,0.55)';
        ctx.lineWidth = 2.2;
      }
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.lineCap = 'butt';
    }

    const liveGroups = (snap.groups || []).filter(
      (g) => !['evacuated', 'RESOLVED', 'REJECTED'].includes(g.status),
    );
    const groupBase = liveGroups.map((g) => toCanvas(g.x, g.y));
    const groupPts = fanOut(groupBase, 24);

    const vehicles = snap.vehicles || [];
    const vehBase = vehicles.map((v) => toCanvas(v.x, v.y));
    const vehPts = fanOut(vehBase, 26).map((p) => nudgeFrom(p, groupPts, 28));

    // --- active routes (unit → group/shelter) ---
    for (const v of vehicles) {
      if (v.status !== 'busy') continue;
      const group = liveGroups.find((g) => g.id === v.assignedGroupId);
      const shelter = (snap.shelters || []).find(
        (s) => s.id === (v.targetShelterId || group?.assignedShelterId),
      );
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
      ctx.strokeStyle = 'rgba(247,185,85,0.45)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([7, 6]);
      ctx.stroke();
      ctx.setLineDash([]);
    }

    // --- depots ---
    for (const d of snap.depots || []) {
      const p = toCanvas(d.x, d.y);
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.fillStyle = 'rgba(52,211,153,0.14)';
      ctx.strokeStyle = 'rgba(52,211,153,0.85)';
      ctx.lineWidth = 1.4;
      roundRect(ctx, -8, -8, 16, 16, 3);
      ctx.fill();
      ctx.stroke();
      ctx.fillStyle = '#6ee7b7';
      ctx.font = 'bold 8px "DM Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText('DEP', 0, 3);
      ctx.textAlign = 'left';
      ctx.restore();
      ctx.fillStyle = 'rgba(148,190,180,0.7)';
      ctx.font = '600 9px "Space Grotesk", sans-serif';
      ctx.fillText(String(d.label || 'Depot').replace(/ Depot$/i, ''), p.x + 12, p.y + 3);
    }

    // --- shelters (badge + occupancy ring) ---
    for (const s of snap.shelters || []) {
      const p = toCanvas(s.x, s.y);
      const cap = s.capacity || 1;
      const frac = Math.max(0, Math.min(1, (s.occupancy || 0) / cap));
      const full = s.open === false || (s.occupancy || 0) >= cap;
      const tint = full ? '#e0564a' : frac >= 0.8 ? '#f7b955' : '#34d399';
      ctx.save();
      ctx.translate(p.x, p.y);
      // occupancy ring
      ctx.beginPath();
      ctx.arc(0, 0, 13, 0, Math.PI * 2);
      ctx.strokeStyle = 'rgba(20,34,37,0.9)';
      ctx.lineWidth = 3;
      ctx.stroke();
      ctx.beginPath();
      ctx.arc(0, 0, 13, -Math.PI / 2, -Math.PI / 2 + frac * Math.PI * 2);
      ctx.strokeStyle = tint;
      ctx.lineWidth = 3;
      ctx.stroke();
      // house glyph
      ctx.fillStyle = full ? 'rgba(224,86,74,0.16)' : 'rgba(52,211,153,0.16)';
      ctx.strokeStyle = tint;
      ctx.lineWidth = 1.4;
      ctx.beginPath();
      ctx.moveTo(0, -6.5);
      ctx.lineTo(6, -1);
      ctx.lineTo(6, 6);
      ctx.lineTo(-6, 6);
      ctx.lineTo(-6, -1);
      ctx.closePath();
      ctx.fill();
      ctx.stroke();
      ctx.restore();
      // labels
      ctx.fillStyle = full ? '#fca5a5' : '#bbf7d0';
      ctx.font = '600 9px "Space Grotesk", sans-serif';
      const name = String(s.label || s.id).split(' ')[0];
      ctx.fillText(name, p.x + 17, p.y - 1);
      ctx.fillStyle = 'rgba(148,190,180,0.7)';
      ctx.font = '9px "DM Mono", monospace';
      ctx.fillText(`${s.occupancy || 0}/${cap}`, p.x + 17, p.y + 10);
    }

    // --- groups (people awaiting rescue) ---
    liveGroups.forEach((g, i) => {
      const p = groupPts[i];
      const critical = g.severity === 'CRITICAL' || (g.vulnerability || 0) >= 90;
      const stranded = String(g.status).toLowerCase().includes('strand');
      const fill = stranded ? '#64748b' : critical ? '#e0564a' : '#f7b955';
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.shadowColor = 'rgba(0,0,0,0.4)';
      ctx.shadowBlur = 4;
      ctx.beginPath();
      ctx.moveTo(0, -12);
      ctx.lineTo(-10, 8);
      ctx.lineTo(10, 8);
      ctx.closePath();
      ctx.fillStyle = fill;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.strokeStyle = 'rgba(255,247,237,0.85)';
      ctx.lineWidth = 1.3;
      ctx.stroke();
      const waiting = Math.max(0, (g.people || 0) - (g.evacuatedPeople || 0));
      ctx.fillStyle = '#0b1a1d';
      ctx.font = 'bold 10px "DM Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(String(waiting), 0, 6);
      ctx.textAlign = 'left';
      ctx.restore();
    });

    // --- vehicles (type icon + status ring + phase) ---
    vehicles.forEach((v, i) => {
      const p = vehPts[i];
      const short = vehicleShort(v.type, v.mode);
      const body = vehicleColor(v.type, v.mode);
      const busy = v.status === 'busy';
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.shadowColor = 'rgba(0,0,0,0.45)';
      ctx.shadowBlur = 5;
      ctx.beginPath();
      ctx.arc(0, 0, 11, 0, Math.PI * 2);
      ctx.fillStyle = body;
      ctx.fill();
      ctx.shadowBlur = 0;
      ctx.beginPath();
      ctx.arc(0, 0, 11, 0, Math.PI * 2);
      ctx.strokeStyle = busy ? '#f7b955' : 'rgba(234,247,255,0.85)';
      ctx.lineWidth = busy ? 2.4 : 1.4;
      ctx.stroke();
      drawVehicleGlyph(ctx, short, '#0b1a1d');
      ctx.restore();
      const phase = String(v.phase || '');
      const phaseLabel =
        phase === 'to_pickup'
          ? 'pickup'
          : phase === 'to_shelter'
          ? 'to shelter'
          : phase === 'loading'
          ? 'loading'
          : phase === 'returning'
          ? 'return'
          : '';
      if (phaseLabel) {
        ctx.fillStyle = '#f7b955';
        ctx.font = '600 8.5px "DM Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(phaseLabel, p.x, p.y - 15);
        ctx.textAlign = 'left';
      }
    });

    // --- footer readout ---
    ctx.fillStyle = 'rgba(130,149,150,0.9)';
    ctx.font = '11px "DM Mono", monospace';
    ctx.textAlign = 'left';
    ctx.fillText(
      `Tick ${snap.tick || 0}  ·  peak ${Math.round(snap.flood?.maxDepthCm || 0)} cm  ·  ${vehicles.length} units · ${(snap.shelters || []).length} shelters`,
      ox - 14,
      oy + usable + 30,
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
        <span><i className="lg water" /> Waterway</span>
        <span><i className="lg route" /> Road</span>
        <span><i className="lg closed" /> Closed road</span>
        <span><i className="lg avail" /> Unit (bus/truck/boat)</span>
        <span><i className="lg assigned" /> Assigned unit</span>
        <span><i className="lg critical" /> People needing help</span>
      </div>
    </div>
  );
}
