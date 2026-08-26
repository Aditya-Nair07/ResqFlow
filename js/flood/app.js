/**
 * ResQFlow-Flood browser client — uses FastAPI when available.
 */
const API = "http://127.0.0.1:8000";
let scenarioId = "urban_flood_default";
let snapshot = null;
let running = false;
let timer = null;

const canvas = document.getElementById("map");
const ctx = canvas.getContext("2d");
const GRID = 25;
const PAD = 20;
const SCALE = (canvas.width - PAD * 2) / GRID;

function wx(x) { return PAD + x * SCALE; }
function wy(y) { return PAD + y * SCALE; }

async function api(path, opts = {}) {
  const res = await fetch(`${API}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

async function checkHealth() {
  try {
    await api("/health");
    document.getElementById("statusLine").textContent = "API connected — deterministic flood simulator active";
    return true;
  } catch {
    document.getElementById("statusLine").textContent = "API offline — start backend: cd backend && python3 -m uvicorn main:app --reload --port 8000";
    return false;
  }
}

async function loadScenarios() {
  try {
    const data = await api("/flood/scenarios");
    const sel = document.getElementById("scenarioSelect");
    sel.innerHTML = "";
    for (const s of data.scenarios) {
      const o = document.createElement("option");
      o.value = s.id;
      o.textContent = s.name;
      sel.appendChild(o);
    }
  } catch (_) {
    const sel = document.getElementById("scenarioSelect");
    sel.innerHTML = '<option value="urban_flood_default">Urban flood default</option>';
  }
}

async function resetSim() {
  scenarioId = document.getElementById("scenarioSelect").value;
  snapshot = (await api(`/flood/reset?scenarioId=${encodeURIComponent(scenarioId)}`, { method: "POST" })).snapshot;
  running = false;
  render();
}

async function stepSim(n = 1) {
  scenarioId = document.getElementById("scenarioSelect").value;
  const body = {
    scenarioId,
    steps: n,
    running,
    rankingMethod: document.getElementById("rankingMethod").value,
    closedLoop: document.getElementById("closedLoop").checked,
  };
  const data = await api("/flood/simulate/step", { method: "POST", body: JSON.stringify(body) });
  snapshot = data.snapshot;
  render();
}

function depthColor(d) {
  if (d < 10) return "rgba(30,58,138,0.15)";
  if (d < 25) return "rgba(37,99,235,0.35)";
  if (d < 45) return "rgba(234,179,8,0.45)";
  return "rgba(239,68,68,0.55)";
}

function drawMap() {
  if (!snapshot) return;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const flood = snapshot.flood || {};
  const depth = flood.depthCm || [];
  const gs = flood.gridSize || GRID;
  for (let y = 0; y < gs; y++) {
    for (let x = 0; x < gs; x++) {
      const d = (depth[y] && depth[y][x]) || 0;
      ctx.fillStyle = depthColor(d);
      ctx.fillRect(wx(x), wy(y), SCALE, SCALE);
    }
  }
  const edgeState = {};
  for (const e of snapshot.roadEdgeStates || []) edgeState[e.id] = e;
  function drawEdge(edge, water) {
    const st = edgeState[edge.id] || {};
    const closed = st.closedForBus;
    ctx.strokeStyle = water ? (closed ? "#0ea5e9" : "#38bdf8") : (closed ? "#ef4444" : "#94a3b8");
    ctx.lineWidth = water ? 2.5 : closed ? 2 : 1.5;
    ctx.setLineDash(water ? [4, 3] : closed ? [6, 4] : []);
    ctx.beginPath();
    ctx.moveTo(wx(edge.from[0]), wy(edge.from[1]));
    ctx.lineTo(wx(edge.to[0]), wy(edge.to[1]));
    ctx.stroke();
    ctx.setLineDash([]);
  }
  for (const e of snapshot.roadEdges || []) drawEdge(e, false);
  for (const e of snapshot.boatLinks || []) drawEdge(e, true);
  ctx.strokeStyle = "rgba(148,163,184,0.15)";
  for (let i = 0; i <= gs; i += 5) {
    ctx.beginPath(); ctx.moveTo(wx(i), wy(0)); ctx.lineTo(wx(i), wy(gs)); ctx.stroke();
    ctx.beginPath(); ctx.moveTo(wx(0), wy(i)); ctx.lineTo(wx(gs), wy(i)); ctx.stroke();
  }
  for (const s of snapshot.shelters || []) {
    ctx.fillStyle = "#22c55e";
    ctx.beginPath(); ctx.arc(wx(s.x), wy(s.y), 7, 0, Math.PI * 2); ctx.fill();
    ctx.fillStyle = "#ecfdf5"; ctx.font = "10px sans-serif"; ctx.fillText("S", wx(s.x) - 3, wy(s.y) + 3);
  }
  for (const g of snapshot.groups || []) {
    const col = g.status === "evacuated" ? "#64748b" : g.status === "stranded" ? "#ef4444" : "#f97316";
    ctx.fillStyle = col;
    ctx.beginPath(); ctx.arc(wx(g.x), wy(g.y), 6, 0, Math.PI * 2); ctx.fill();
  }
  for (const v of snapshot.vehicles || []) {
    ctx.fillStyle = v.mode === "water" ? "#38bdf8" : "#a78bfa";
    ctx.fillRect(wx(v.x) - 5, wy(v.y) - 5, 10, 10);
    if (v.status === "busy") {
      ctx.strokeStyle = "#fbbf24";
      ctx.strokeRect(wx(v.x) - 7, wy(v.y) - 7, 14, 14);
    }
  }
  ctx.fillStyle = "#94a3b8";
  ctx.font = "11px sans-serif";
  const closedN = (snapshot.roadEdgeStates || []).filter(e => e.closedForBus).length;
  ctx.fillText(`Tick ${snapshot.tick || 0} · max depth ${Math.round(flood.maxDepthCm || 0)} cm · ${closedN} closed roads`, PAD, canvas.height - 8);
}

function renderPanels() {
  if (!snapshot) return;
  const m = snapshot.metrics || {};
  document.getElementById("metrics").innerHTML = `
    <div>People evacuated: <strong>${m.peopleEvacuated || 0}</strong></div>
    <div>Repairs: ${m.repairs || 0} · Reroutes: ${m.reroutes || 0}</div>
    <div>Unsafe (open-loop): ${m.unsafeActuations || 0} · Stranded: ${m.strandedGroups || 0}</div>
    <div>Citizen reports: ${m.citizenReports || 0}</div>`;
  document.getElementById("groups").innerHTML = (snapshot.groups || []).map(g => `
    <div class="border border-slate-700 rounded p-2">
      <div class="font-semibold">${g.label || g.id}</div>
      <div>${g.people} people · Vuln ${g.vulnerability} · ${g.status}</div>
      <div class="text-slate-400">Deadline tick ${g.deadlineTick}</div>
    </div>`).join("");
  document.getElementById("shelters").innerHTML = (snapshot.shelters || []).map(s => `
    <div>${s.label}: ${s.occupancy || 0}/${s.capacity}</div>`).join("");
  const traces = snapshot.recentTraces || [];
  document.getElementById("trace").textContent = traces.length ? JSON.stringify(traces[traces.length - 1], null, 2) : "—";
  const cr = snapshot.lastCitizenReport;
  document.getElementById("citizenFeedback").textContent = cr
    ? `${cr.message}\nTick ${cr.tick} · severity ${cr.severity}\nDepth now ${cr.effects?.depthAtReport ?? "?"} cm` +
      (cr.effects?.roadsForcedClosed?.length ? `\nRoads closed: ${cr.effects.roadsForcedClosed.join(", ")}` : "") +
      (cr.effects?.groupCreated ? `\nGroup created: ${cr.effects.groupCreated}` : "")
    : "— none yet. Open “Citizen report” and submit waterlogging.";
}

function render() {
  drawMap();
  renderPanels();
}

document.getElementById("resetBtn").addEventListener("click", () => resetSim().catch(console.error));
document.getElementById("stepBtn").addEventListener("click", () => stepSim(1).catch(console.error));
document.getElementById("runBtn").addEventListener("click", () => {
  running = true;
  if (timer) clearInterval(timer);
  timer = setInterval(() => stepSim(1).catch(console.error), 800);
});
document.getElementById("pauseBtn").addEventListener("click", () => {
  running = false;
  if (timer) clearInterval(timer);
});

// Poll so citizen reports submitted from report.html appear on the ops dashboard
setInterval(async () => {
  if (!scenarioId) return;
  try {
    const snap = await api(`/flood/snapshot?scenarioId=${encodeURIComponent(scenarioId)}`);
    if (snap.lastCitizenReport && (!snapshot?.lastCitizenReport || snap.lastCitizenReport.tick !== snapshot.lastCitizenReport?.tick || snap.metrics?.citizenReports !== snapshot.metrics?.citizenReports)) {
      snapshot = snap;
      render();
    } else if (snapshot && snap.tick === snapshot.tick) {
      // still refresh citizen feedback if report arrived without tick change
      if (JSON.stringify(snap.lastCitizenReport) !== JSON.stringify(snapshot.lastCitizenReport)) {
        snapshot = snap;
        render();
      }
    }
  } catch (_) { /* offline */ }
}, 1500);

(async () => {
  await checkHealth();
  await loadScenarios();
  if (await checkHealth()) await resetSim();
})();
