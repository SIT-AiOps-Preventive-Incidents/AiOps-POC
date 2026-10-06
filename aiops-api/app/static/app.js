/* AIOps One Solution - single-page UI (no build step). */
const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const api = async (path, opts = {}) => {
  const r = await fetch(path, {headers: {"Content-Type": "application/json"}, ...opts,
    body: opts.body ? JSON.stringify(opts.body) : undefined});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
};
const toast = (m) => { const t = $("#toast"); t.textContent = m; t.style.display = "block"; clearTimeout(t._h); t._h = setTimeout(() => t.style.display = "none", 3500); };
const pct = (v, d = 1) => v == null ? "-" : (v * 100).toFixed(d) + "%";
const num = (v, d = 1) => v == null ? "-" : Number(v).toFixed(d);
const ms = (v) => v == null ? "-" : v >= 1000 ? (v / 1000).toFixed(2) + " s" : Math.round(v) + " ms";
const ago = (ts) => { if (!ts) return "-"; const s = Date.now() / 1000 - ts; if (s < 60) return Math.round(s) + "s ago"; if (s < 3600) return Math.round(s / 60) + "m ago"; if (s < 86400) return Math.round(s / 3600) + "h ago"; return Math.round(s / 86400) + "d ago"; };
const dur = (s) => s == null ? "-" : s < 60 ? Math.round(s) + "s" : s < 3600 ? Math.round(s / 60) + "m " + Math.round(s % 60) + "s" : (s / 3600).toFixed(1) + "h";
const time = (ts) => ts ? new Date(ts * 1000).toLocaleTimeString() : "-";
const STATUS_TXT = {open: "Open", analyzing: "AI analyzing", awaiting_approval: "Awaiting approval", remediating: "Remediating",
  verifying: "Verifying fix", resolved: "Resolved", rejected: "Rejected", closed: "Closed", remediation_failed: "Fix failed"};
const badge = (s) => `<span class="badge b-${esc(s)}">${esc(STATUS_TXT[s] || s)}</span>`;

const I = {
  map: '<circle cx="5" cy="12" r="2.5"/><circle cx="12" cy="5" r="2.5"/><circle cx="12" cy="19" r="2.5"/><circle cx="19" cy="12" r="2.5"/><path d="M7.3 11 10 6.6M7.3 13 10 17.4M14 6.6l3 4.4M14 17.4l3-4.4"/>',
  overview: '<path d="M3 3h7v9H3zM14 3h7v5h-7zM14 12h7v9h-7zM3 16h7v5H3z"/>',
  services: '<circle cx="12" cy="12" r="3"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/><path d="M6 7l4 3M18 7l-4 3M6 17l4-3M18 17l-4-3"/>',
  infra: '<rect x="3" y="4" width="18" height="6" rx="1"/><rect x="3" y="14" width="18" height="6" rx="1"/><path d="M7 7h.01M7 17h.01"/>',
  problems: '<path d="M12 3 2 20h20z"/><path d="M12 10v4M12 17h.01"/>',
  deploy: '<circle cx="6" cy="6" r="2"/><circle cx="6" cy="18" r="2"/><circle cx="18" cy="12" r="2"/><path d="M6 8v8M8 6c6 0 8 2 8 4"/>',
  plug: '<path d="M9 2v6M15 2v6M6 8h12v4a6 6 0 0 1-12 0zM12 18v4"/>',
  server: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 7h8M8 11h8M8 15h3"/>',
  brain: '<path d="M9 3a3 3 0 0 0-3 3 3 3 0 0 0-2 5 3 3 0 0 0 2 5 3 3 0 0 0 6 2V3a3 3 0 0 0-3 0zM15 3a3 3 0 0 1 3 3 3 3 0 0 1 2 5 3 3 0 0 1-2 5 3 3 0 0 1-6 2"/>',
  book: '<path d="M4 4h10a4 4 0 0 1 4 4v12H8a4 4 0 0 1-4-4z"/><path d="M8 8h6"/>',
  bell: '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 20a2 2 0 0 0 4 0"/>',
  bolt: '<path d="M13 2 4 14h7l-1 8 9-12h-7z"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
};
const icon = (k) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">${I[k]}</svg>`;

const MENU = [
  ["Observe", [["#/", "Overview", "overview"], ["#/map", "Service Map", "map"], ["#/services", "Services", "services"], ["#/infra", "Infrastructure", "infra"],
    ["#/problems", "Problems", "problems"], ["#/deployments", "Deployments", "deploy"]]],
  ["Connect", [["#/connect/app", "Connect App", "plug"], ["#/connect/infra", "Connect Infrastructure", "server"]]],
  ["Agentic AI", [["#/skills", "Skills & Scoring", "brain"], ["#/runbooks", "Runbook Memory", "book"], ["#/notifications", "Notifications", "bell"]]],
  ["Demo", [["#/chaos", "Chaos Scenarios", "bolt"]]],
  ["", [["#/settings", "Settings", "gear"]]],
];
let openCount = 0;
function renderMenu() {
  const h = location.hash || "#/";
  $("#menu").innerHTML = MENU.map(([sec, items]) => (sec ? `<div class="navsec">${sec}</div>` : `<div class="navsec"></div>`) +
    items.map(([href, label, ic]) => {
      const active = href === "#/" ? h === "#/" || h === "" : h.startsWith(href);
      const cnt = href === "#/problems" && openCount ? `<span class="cnt">${openCount}</span>` : "";
      return `<a class="navitem ${active ? "active" : ""}" href="${href}">${icon(ic)}<span>${label}</span>${cnt}</a>`;
    }).join("")).join("");
}

/* ---------------- charts ---------------- */
function chart(points, {color = "#1496ff", h = 110, fmt = (v) => num(v, 2), title = ""} = {}) {
  const pts = (points || []).filter((p) => p[1] != null);
  const W = 600;
  if (pts.length < 2) return `<div class="card"><h3>${esc(title)}</h3><div class="empty">No data yet</div></div>`;
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), ymax = Math.max(...ys) * 1.15 || 1;
  const X = (x) => ((x - x0) / (x1 - x0 || 1)) * W, Y = (y) => h - 4 - (y / ymax) * (h - 18);
  const line = pts.map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" ");
  const id = "g" + Math.random().toString(36).slice(2, 8);
  return `<div class="card"><div class="row between"><h3>${esc(title)}</h3><b>${fmt(ys[ys.length - 1])}</b></div>
  <svg class="chart" viewBox="0 0 ${W} ${h}" preserveAspectRatio="none" style="height:${h}px">
   <defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="${color}" stop-opacity=".35"/><stop offset="1" stop-color="${color}" stop-opacity="0"/></linearGradient></defs>
   <line x1="0" x2="${W}" y1="${Y(ymax / 1.15)}" y2="${Y(ymax / 1.15)}" stroke="#2e3050" stroke-dasharray="3 4"/>
   <polygon points="0,${h} ${line} ${W},${h}" fill="url(#${id})"/>
   <polyline points="${line}" fill="none" stroke="${color}" stroke-width="2" vector-effect="non-scaling-stroke"/>
  </svg><div class="row between small dim"><span>${time(x0)}</span><span>max ${fmt(ymax / 1.15)}</span><span>${time(x1)}</span></div></div>`;
}
const gauge = (v, warn = 70, crit = 90) => {
  const c = v == null ? "#6c6e8c" : v >= crit ? "#dc3545" : v >= warn ? "#fd8232" : "#2ab06f";
  return `<div class="gauge"><div style="width:${Math.min(v || 0, 100)}%;background:${c}"></div></div>`;
};

/* ---------------- router ---------------- */
let timer = null;
const routes = [
  [/^#?\/?$/, overview], [/^#\/map$/, serviceMap], [/^#\/services$/, services], [/^#\/services\/(.+)$/, serviceDetail], [/^#\/infra$/, infra],
  [/^#\/infra\/(.+)$/, hostDetail], [/^#\/problems$/, problems], [/^#\/problems\/(\d+)$/, problemDetail],
  [/^#\/deployments$/, deploymentsView], [/^#\/connect\/app$/, connectApp], [/^#\/connect\/infra$/, connectInfra],
  [/^#\/skills$/, skillsView], [/^#\/runbooks$/, runbooksView], [/^#\/notifications$/, notificationsView],
  [/^#\/chaos$/, chaosView], [/^#\/settings$/, settingsView],
];
async function route() {
  clearInterval(timer);
  renderMenu();
  const h = location.hash || "#/";
  for (const [re, fn] of routes) {
    const m = h.match(re);
    if (m) {
      const run = async (first) => { try { await fn(...m.slice(1), first); } catch (e) { if (first) $("#view").innerHTML = `<div class="card red">${esc(e.message)}</div>`; } };
      await run(true);
      if (fn.refresh) timer = setInterval(() => run(false), fn.refresh);
      return;
    }
  }
  $("#view").innerHTML = '<div class="empty">Not found</div>';
}
window.addEventListener("hashchange", route);
const crumb = (a, b = "") => $("#crumb").innerHTML = esc(a) + (b ? ` <span>/ ${esc(b)}</span>` : "");
const keepFocus = () => document.activeElement && ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName);

/* ---------------- overview ---------------- */
async function overview(first) {
  crumb("Overview");
  const d = await api("/api/overview");
  status(d);
  const k = d.kpi;
  const tile = (l, v, hint = "", cls = "") => `<div class="card tile"><div class="lbl">${l}</div><div class="val ${cls}">${v}</div><div class="hint">${hint}</div></div>`;
  $("#view").innerHTML = `
  <h1>Environment overview</h1><p class="sub">Customer services and infrastructure connected to the platform, monitored in real time by the anomaly detector and the agentic RCA pipeline.</p>
  <div class="grid g5 mb">
    ${tile("Open problems", k.open, `${k.awaiting_approval} awaiting approval`, k.open ? "red" : "green")}
    ${tile("Mean time to detect", dur(k.mttd_s), "anomaly start to problem")}
    ${tile("Mean time to RCA", dur(k.mtta_s), "problem to AI report")}
    ${tile("Mean time to resolve", dur(k.mttr_s), "problem to verified fix")}
    ${tile("Avg RCA score", k.avg_score ? k.avg_score + " / 5" : "-", `${k.total} problems total`)}
  </div>
  <div class="grid g32">
    <div class="card"><div class="row between"><h2>Services</h2><a href="#/services" class="small">All services</a></div>
      <table><tr><th>Service</th><th>Version</th><th>Req/s</th><th>Failure rate</th><th>p95</th></tr>
      ${d.services.map((s) => `<tr class="click" onclick="location.hash='#/services/${s.service}'"><td><div class="row"><span class="dot ${s.status}"></span>${esc(s.service)}</div></td>
        <td class="mono small">v${esc(s.version)} <span class="dim">${esc(s.commit)}</span></td><td>${num(s.rps, 2)}</td>
        <td class="${s.error_rate > 0.05 ? "red" : ""}">${pct(s.error_rate)}</td><td>${ms(s.p95_ms)}</td></tr>`).join("")}</table>
    </div>
    <div class="card"><div class="row between"><h2>Open problems</h2><a href="#/problems" class="small">All problems</a></div>
      ${d.open_problems.length ? d.open_problems.map((p) => `<div class="card click problem-card ${p.status} mt8" onclick="location.hash='#/problems/${p.id}'">
        <div class="row between"><b>P-${p.id}</b>${badge(p.status)}</div><div class="mt8">${esc(p.title)}</div>
        <div class="small dim mt8">${esc(p.entity_type)}: ${esc(p.entity)} &middot; ${ago(p.detected_at)}</div></div>`).join("")
      : '<div class="empty"><span class="green">No open problems</span><br>All monitored entities are healthy</div>'}
    </div>
  </div>
  <div class="card mt"><div class="row between"><h2>Hosts</h2><a href="#/infra" class="small">Infrastructure</a></div>
    <div class="grid g4">${d.hosts.map(hostCard).join("")}</div></div>
  <div class="card mt"><h2>Service flow</h2><div id="topo" class="topo dim small">loading...</div></div>`;
  loadTopo();
}
overview.refresh = 10000;
async function loadTopo() {
  const edges = await api("/api/topology").catch(() => []);
  const el = $("#topo"); if (!el) return;
  el.innerHTML = edges.length ? edges.map((e) => `<span class="pill">${esc(e.from)}</span><span class="arrow">&rarr;</span><span class="pill">${esc(e.to)}</span><span class="dim small" style="margin-right:18px">${e.count} calls</span>`).join("") : "no traces in the last 5 min";
}
const hostCard = (h) => `<div class="card click" onclick="location.hash='#/infra/${esc(h.name)}'">
  <div class="row between"><div class="row"><span class="dot ${h.status}"></span><b>${esc(h.name)}</b></div><span class="small dim">${esc(h.address)}</span></div>
  <div class="small mt8">CPU ${num(h.cpu)}%</div>${gauge(h.cpu)}<div class="small mt8">Memory ${num(h.mem)}%</div>${gauge(h.mem)}
  <div class="small mt8">Disk ${num(h.disk)}%</div>${gauge(h.disk, 80, 90)}</div>`;
function status(d) {
  openCount = d.kpi.open; renderMenu();
  const l = d.llm; $("#llmpill").className = "pill " + (l.up && l.models.includes(l.active) ? "ok" : "bad");
  $("#llmpill").textContent = "LLM " + (l.up ? l.active : "offline");
  const det = d.detector; const fresh = det.ts && Date.now() / 1000 - det.ts < 60;
  $("#detpill").className = "pill " + (fresh ? "ok" : "bad"); $("#detpill").textContent = fresh ? `Detector live (${det.checks} checks)` : "Detector starting";
  $("#grafana").href = d.grafana_url;
  $("#navfoot").innerHTML = `Telemetry: OpenTelemetry &rarr; Prometheus / Loki / Tempo<br>Model: ${esc(l.active)} (CPU)`;
}

/* ---------------- services ---------------- */
async function services() {
  crumb("Services");
  const apps = await api("/api/apps");
  $("#view").innerHTML = `<div class="row between"><div><h1>Services</h1><p class="sub">Applications sending OpenTelemetry traces and logs. Metrics are derived from spans and tagged with version and commit.</p></div>
    <a class="btn" href="#/connect/app">+ Connect app</a></div>
  <div class="card"><table><tr><th>Service</th><th>Team</th><th>Version / commit</th><th>Req/s</th><th>Failure rate</th><th>p95</th><th>Status</th></tr>
  ${apps.map((a) => `<tr class="click" onclick="location.hash='#/services/${a.service_name}'"><td><div class="row"><span class="dot ${a.status}"></span><div><b>${esc(a.name)}</b><div class="small dim">${esc(a.service_name)} &middot; ${esc(a.language)}</div></div></div></td>
   <td>${esc(a.team)}</td><td class="mono small">v${esc(a.version)} ${esc(a.commit)}<div class="dim">${ago(a.deployed_at)}</div></td><td>${num(a.rps, 2)}</td>
   <td class="${a.error_rate > 0.05 ? "red" : ""}">${pct(a.error_rate)}</td><td>${ms(a.p95_ms)}</td>
   <td>${a.problem_id ? `<a href="#/problems/${a.problem_id}" onclick="event.stopPropagation()" class="red">P-${a.problem_id}</a>` : a.status}</td></tr>`).join("")}
  </table></div>`;
}
services.refresh = 10000;

async function serviceDetail(svc) {
  crumb("Services", svc);
  const d = await api(`/api/services/${svc}`);
  const h = d.health;
  $("#view").innerHTML = `
  <div class="row between mb"><div><h1 class="row"><span class="dot ${h.status}"></span>${esc(d.app.name)}</h1>
    <div class="muted small">${esc(d.app.service_name)} &middot; ${esc(d.app.team)} &middot; ${esc(d.app.repo)} &middot; v${esc(h.version)} (${esc(h.commit)})</div></div>
    ${h.problem_id ? `<a class="btn red" href="#/problems/${h.problem_id}">Open problem P-${h.problem_id}</a>` : '<span class="badge b-resolved">Healthy</span>'}</div>
  <div class="grid g3">${chart(d.series.rps, {title: "Throughput (req/s)"})}${chart(d.series.error_rate, {title: "Failure rate", color: "#dc3545", fmt: (v) => pct(v)})}
    ${chart(d.series.p95, {title: "Response time p95", color: "#fd8232", fmt: ms})}</div>
  <div class="grid g2 mt">
    <div class="card"><h2>Endpoints (5 min)</h2><table><tr><th>Request</th><th>Req/s</th><th>Failure rate</th></tr>
      ${d.endpoints.map((e) => `<tr><td class="mono small">${esc(e.name)}</td><td>${e.rps}</td><td class="${e.error_rate > 0.05 ? "red" : ""}">${pct(e.error_rate)}</td></tr>`).join("")}</table></div>
    <div class="card"><h2>Failure rate by version (commit-level)</h2><table><tr><th>Version</th><th>Commit</th><th>Req/s</th><th>Failure rate</th></tr>
      ${d.versions.map((v) => `<tr><td>v${esc(v.version)}</td><td class="mono">${esc(v.commit)}</td><td>${v.rps}</td><td class="${v.error_rate > 0.05 ? "red" : ""}">${pct(v.error_rate)}</td></tr>`).join("")}</table></div>
  </div>
  <div class="grid g2 mt">
    <div class="card"><h2>Recent traces</h2><table><tr><th>Trace</th><th>Root</th><th>Duration</th><th>Start</th></tr>
      ${d.traces.map((t) => `<tr class="click" onclick="showTrace('${t.traceID}')"><td class="mono small">${esc(t.traceID.slice(0, 12))}</td><td class="small">${esc(t.rootServiceName)} ${esc(t.rootTraceName)}</td><td>${t.durationMs ?? 0} ms</td><td class="small dim">${time(t.startTimeUnixNano / 1e9)}</td></tr>`).join("")}</table></div>
    <div class="card"><h2>Deployments</h2><table><tr><th>Version</th><th>Commit</th><th>By</th><th>When</th></tr>
      ${d.deployments.map((x) => `<tr><td>v${esc(x.version)}</td><td class="mono">${esc(x.commit_hash)}</td><td class="small">${esc(x.author)}<div class="dim">${esc(x.message)}</div></td><td class="small">${ago(x.ts)}</td></tr>`).join("")}</table></div>
  </div>
  <div class="card mt"><h2>Logs (15 min)</h2>${logLines(d.logs)}</div>`;
}
serviceDetail.refresh = 15000;
const logLines = (logs) => logs.length ? logs.map((l) => `<div class="logline"><span class="dim">${time(l.ts)}</span><span class="lv lv-${esc(l.level)}">${esc(l.level)}</span><span>${esc(l.line)}</span></div>`).join("") : '<div class="empty">No logs</div>';

async function showTrace(id) {
  const spans = await api(`/api/traces/${id}`);
  if (!spans.length) return toast("Trace not found (may not be flushed yet)");
  const t0 = Math.min(...spans.map((s) => s.start)), t1 = Math.max(...spans.map((s) => s.end)), span = t1 - t0 || 1;
  const depth = {}; const byId = Object.fromEntries(spans.map((s) => [s.id, s]));
  const dep = (s) => depth[s.id] ?? (depth[s.id] = byId[s.parent] ? dep(byId[s.parent]) + 1 : 0);
  openModal(`<h2>Distributed trace <span class="mono dim">${esc(id)}</span></h2><p class="sub">${spans.length} spans &middot; ${ms(span)}</p>
   ${spans.map((s) => `<div class="wf-row"><div style="padding-left:${dep(s) * 14}px" class="${s.error ? "red" : ""}"><b>${esc(s.service)}</b> <span class="muted">${esc(s.name)}</span></div>
    <div class="wf"><div class="bar ${s.error ? "err" : ""}" style="left:${((s.start - t0) / span) * 100}%;width:${Math.max(((s.end - s.start) / span) * 100, 0.4)}%"></div></div>
    <div class="small">${ms(s.end - s.start)}</div></div>${s.error && s.status_msg ? `<div class="small red" style="padding-left:${dep(s) * 14 + 8}px">${esc(s.status_msg)}</div>` : ""}`).join("")}`);
}

/* ---------------- service map (Smartscape style) ---------------- */
async function serviceMap() {
  crumb("Service Map");
  const d = await api("/api/servicemap");
  const multi = new Set(d.nodes.filter((n) => n.instances.length).map((n) => n.id));
  const byId = Object.fromEntries(d.nodes.map((n) => [n.id, n]));
  // Graph at instance level for multi-instance services, service level otherwise.
  const gnodes = {}, gedges = [];
  const add = (id, o) => { gnodes[id] = gnodes[id] || {id, ...o}; };
  add("internet", {label: "Clients", sub: "Internet", kind: "client"});
  for (const n of d.nodes) {
    if (multi.has(n.id)) n.instances.forEach((i) => add(i.id, {label: i.id, sub: `${n.id} instance`, kind: "instance", svc: n.id, m: i, problem: i.problem_id || n.problem_id}));
    else add(n.id, {label: n.id, sub: n.kind === "network" ? (n.id.includes("firewall") ? "firewall" : "load balancer") : `service · ${n.owner || ""}`, kind: n.kind, svc: n.id, m: n, problem: n.problem_id, connected: n.connected});
  }
  for (const e of d.edges) if (!multi.has(e.from) && !multi.has(e.to)) gedges.push(e);
  for (const e of d.instance_edges) {
    const f = multi.has(e.from_service) ? e.from : e.from_service, t = multi.has(e.to_service) ? e.to : e.to_service;
    if (gnodes[f] && gnodes[t] && f !== t) gedges.push({...e, from: f, to: t});
  }
  for (const r of d.entry) if (gnodes[r]) { const n = byId[r]; gedges.push({from: "internet", to: r, rps: n?.rps, error_rate: null, share: 1}); }
  // layers = longest path from the clients node
  const layer = {internet: 0};
  for (let k = 0; k < 10; k++) for (const e of gedges) if (layer[e.from] != null) layer[e.to] = Math.max(layer[e.to] ?? 0, layer[e.from] + 1);
  const maxL = Math.max(0, ...Object.values(layer));
  const cols = {};
  Object.values(gnodes).forEach((n) => { const l = layer[n.id] ?? maxL + 1; n.layer = l; (cols[l] = cols[l] || []).push(n); });
  const W = 178, H = 70, CW = 238, RH = 104, top = 40;
  const rows = Math.max(...Object.values(cols).map((c) => c.length));
  const height = top + rows * RH + 90, width = 40 + (Math.max(...Object.keys(cols).map(Number)) + 1) * CW;
  Object.entries(cols).forEach(([l, ns]) => ns.sort((a, b) => a.label.localeCompare(b.label)).forEach((n, i) => {
    n.x = 30 + Number(l) * CW; n.y = top + (rows - ns.length) * RH / 2 + i * RH;
  }));
  const thr = 0.05;
  const health = (n) => n.kind === "client" ? "client" : n.problem ? "bad" : !n.m || n.m.rps == null ? "nodata" : n.m.error_rate > thr ? "bad" : "ok";
  const edgesSvg = gedges.map((e) => {
    const a = gnodes[e.from], b = gnodes[e.to]; if (!a || !b) return "";
    const x1 = a.x + W, y1 = a.y + H / 2, x2 = b.x - 6, y2 = b.y + H / 2, mx = (x1 + x2) / 2;
    const bad = (e.error_rate ?? 0) > thr, w = Math.max(1.2, Math.min(6, (e.rps || 0) * 0.8));
    let split = "";
    if (multi.has(b.svc) && !multi.has(a.svc)) {
      const tot = gedges.filter((x) => x.from === e.from && gnodes[x.to]?.svc === b.svc).reduce((t, x) => t + (x.rps || 0), 0);
      if (tot) split = " · " + Math.round(((e.rps || 0) / tot) * 100) + "% of LB";
    }
    const lbl = `${e.rps != null ? num(e.rps, 1) + " req/s" : ""}${split}${bad ? " · " + pct(e.error_rate, 0) + " err" : ""}`;
    return `<path d="M${x1} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2} ${y2}" class="sm-edge ${bad ? "bad" : ""}" style="stroke-width:${w}" marker-end="url(#smh${bad ? "b" : ""})"/>
      <text x="${mx}" y="${(y1 + y2) / 2 - 6}" class="sm-elbl ${bad ? "bad" : ""}" text-anchor="middle">${esc(lbl)}</text>`;
  }).join("");
  const nodesSvg = Object.values(gnodes).map((n) => {
    const h = health(n), m = n.m || {};
    const href = n.kind === "client" ? "" : n.problem ? `#/problems/${n.problem}` : `#/services/${n.svc}`;
    return `<g class="sm-node ${h}" ${href ? `onclick="location.hash='${href}'"` : ""}>
      <rect x="${n.x}" y="${n.y}" width="${W}" height="${H}" rx="${n.kind === "network" ? 2 : 8}"/>
      <circle cx="${n.x + 14}" cy="${n.y + 18}" r="5" class="sm-dot"/>
      <text x="${n.x + 26}" y="${n.y + 22}" class="sm-name">${esc(n.label)}</text>
      <text x="${n.x + 12}" y="${n.y + 40}" class="sm-sub">${esc(n.sub)}</text>
      ${n.kind !== "client" ? `<text x="${n.x + 12}" y="${n.y + 58}" class="sm-kpi">${m.rps != null ? num(m.rps, 1) + " req/s" : "no traffic"}${m.error_rate != null ? " · " + pct(m.error_rate, 1) : ""}${m.p95_ms ? " · " + ms(m.p95_ms) : ""}</text>` : `<text x="${n.x + 12}" y="${n.y + 58}" class="sm-kpi">via edge-firewall</text>`}
      ${n.problem ? `<text x="${n.x + W - 10}" y="${n.y + 22}" class="sm-prob" text-anchor="end">P-${n.problem}</text>` : ""}</g>`;
  }).join("");
  $("#view").innerHTML = `<div class="row between wrap"><div><h1>Service map</h1><p class="sub">Every hop a request takes, from the client through the firewall and load balancer to each instance. Edges come from ${d.traces_sampled} sampled traces; rates come from span metrics. Click a node to open it.</p></div>
    <div class="row small"><span class="row"><span class="dot healthy"></span>healthy</span><span class="row"><span class="dot problem"></span>problem / errors</span><span class="row"><span class="dot no-data"></span>no traffic</span></div></div>
  <div class="card" style="overflow-x:auto"><svg viewBox="0 0 ${width} ${height}" style="width:100%;min-width:${Math.min(width, 1100)}px;height:auto" class="smap">
    <defs><marker id="smh" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 10 5 0 10z" fill="#6c6e8c"/></marker>
    <marker id="smhb" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto"><path d="M0 0 10 5 0 10z" fill="#dc3545"/></marker></defs>
    ${Object.keys(cols).map((l) => `<text x="${30 + l * CW}" y="22" class="sm-layer">${["CLIENTS", "PERIMETER", "LOAD BALANCING", "WEB TIER", "APP TIER", "BACKEND", "DATA"][l] || "TIER " + l}</text>`).join("")}
    ${edgesSvg}${nodesSvg}
    <rect x="20" y="${height - 50}" width="${width - 40}" height="36" rx="6" class="sm-host"/>
    <text x="34" y="${height - 27}" class="sm-sub">Host layer: ${d.hosts.map((h) => esc(h.name) + " (" + esc(h.address) + ")").join(", ")} - every process above runs as a container on this host</text>
  </svg></div>
  <div class="grid g2 mt">
    <div class="card"><h2>Load balancer split</h2>${d.nodes.filter((n) => n.instances.length).map((n) => `<div class="mb"><b>${esc(n.id)}</b>${n.instances.map((i) => { const share = n.rps ? i.rps / n.rps : 0; return `<div class="row small mt8"><span style="width:90px">${esc(i.id)}</span><div class="gauge" style="flex:1"><div style="width:${share * 100}%;background:${i.error_rate > thr ? "#dc3545" : "#1496ff"}"></div></div><span style="width:150px;text-align:right">${num(i.rps, 2)} req/s · ${pct(i.error_rate)}</span></div>`; }).join("")}</div>`).join("") || '<div class="dim">No multi-instance services</div>'}</div>
    <div class="card"><h2>Hops</h2><table><tr><th>From</th><th>To</th><th>Req/s</th><th>Errors</th></tr>${gedges.map((e) => `<tr><td>${esc(e.from)}</td><td>${esc(e.to)}</td><td>${num(e.rps, 2)}</td><td class="${(e.error_rate ?? 0) > thr ? "red" : ""}">${e.error_rate == null ? "-" : pct(e.error_rate)}</td></tr>`).join("")}</table></div>
  </div>`;
}
serviceMap.refresh = 15000;

/* ---------------- infrastructure ---------------- */
async function infra() {
  crumb("Infrastructure");
  const hosts = await api("/api/hosts");
  $("#view").innerHTML = `<div class="row between"><div><h1>Infrastructure</h1><p class="sub">Hosts connected via node_exporter. Prometheus discovers them from the registry automatically.</p></div>
   <a class="btn" href="#/connect/infra">+ Connect infrastructure</a></div><div class="grid g3">${hosts.map(hostCard).join("")}</div>`;
}
infra.refresh = 10000;
async function hostDetail(name) {
  crumb("Infrastructure", name);
  const d = await api(`/api/hosts/${name}`);
  const h = d.host;
  $("#view").innerHTML = `<div class="row between mb"><div><h1 class="row"><span class="dot ${h.status}"></span>${esc(h.name)}</h1><div class="muted small">${esc(h.address)} &middot; ${esc(h.os)} &middot; ${esc(h.environment)}</div></div>
   ${h.problem_id ? `<a class="btn red" href="#/problems/${h.problem_id}">Open problem P-${h.problem_id}</a>` : ""}</div>
  <div class="grid g4">${chart(d.series.cpu, {title: "CPU %", fmt: (v) => num(v) + "%"})}${chart(d.series.mem, {title: "Memory %", color: "#9b5cff", fmt: (v) => num(v) + "%"})}
   ${chart(d.series.disk, {title: "Disk %", color: "#00b4c5", fmt: (v) => num(v) + "%"})}${chart(d.series.load, {title: "Load 1m", color: "#fd8232"})}</div>
  ${d.containers.length ? `<div class="card mt"><h2>Containers on this host</h2><table><tr><th>Container</th><th>Image</th><th>Status</th><th>CPU</th><th>Memory</th></tr>
   ${d.containers.map((c) => `<tr><td><b>${esc(c.name)}</b></td><td class="mono small">${esc(c.image)}</td><td>${esc(c.status)}</td><td class="${c.cpu_pct > 50 ? "red" : ""}">${num(c.cpu_pct)}%</td><td>${num(c.mem_mb, 0)} / ${c.mem_limit_mb} MB</td></tr>`).join("")}</table></div>` : ""}`;
}
hostDetail.refresh = 15000;

/* ---------------- problems ---------------- */
async function problems() {
  crumb("Problems");
  const rows = await api("/api/incidents");
  $("#view").innerHTML = `<h1>Problems</h1><p class="sub">Every anomaly the detector raised, the agent's root cause, and where it stands in the approval workflow.</p>
  <div class="card">${rows.length ? `<table><tr><th>ID</th><th>Problem</th><th>Severity</th><th>Status</th><th>Root cause</th><th>Confidence</th><th>Detected</th><th>Score</th></tr>
  ${rows.map((p) => `<tr class="click" onclick="location.hash='#/problems/${p.id}'"><td><b>P-${p.id}</b></td><td>${esc(p.title)}<div class="small dim">${esc(p.entity_type)}: ${esc(p.entity)}</div></td>
   <td><span class="badge b-${p.severity}">${esc(p.severity)}</span></td><td>${badge(p.status)}</td><td class="small" style="max-width:380px">${esc(p.root_cause || "-")}</td>
   <td>${p.confidence ? Math.round(p.confidence * 100) + "%" : "-"}</td><td class="small">${ago(p.detected_at)}</td><td>${p.score ? p.score + "/5" : "-"}</td></tr>`).join("")}</table>`
  : '<div class="empty">No problems yet. Trigger one from <a href="#/chaos">Chaos Scenarios</a>.</div>'}</div>`;
}
problems.refresh = 8000;

let selCand = 0, starScore = 0;
async function problemDetail(id, first) {
  crumb("Problems", "P-" + id);
  if (keepFocus()) return;
  const p = await api(`/api/incidents/${id}`);
  if (first) { selCand = 0; starScore = p.score || 0; }
  const s = p.signal || {}, f = p.facts || {}, a = p.action || {};
  const waiting = ["awaiting_approval", "remediation_failed"].includes(p.status);
  const steps = p.steps || [];
  const keep = Object.fromEntries(["approver", "apcomment", "fbtext"].map((k) => [k, $("#" + k)?.value]));
  const openDetails = [...document.querySelectorAll("#view details")].map((d) => d.open);
  $("#view").innerHTML = `
  <div class="card problem-card ${p.status} mb"><div class="row between wrap">
    <div><div class="row"><span class="badge b-${p.severity}">${esc(p.severity)}</span>${badge(p.status)}${p.path ? `<span class="badge b-${p.path}">${p.path === "known" ? "Known incident - runbook reused" : "New incident - fresh RCA"}</span>` : ""}</div>
      <h1 class="mt8">P-${p.id} ${esc(p.title)}</h1>
      <div class="muted small">Detected on ${esc(p.entity_type)} <b>${esc(p.entity)}</b>${(s.affected || []).length ? ` &middot; also affected: ${s.affected.map(esc).join(", ")}` : ""}
       &middot; started ${time(p.started_at)} &middot; detected ${time(p.detected_at)} (${dur(p.detected_at - p.started_at)})
       ${p.analyzed_at ? ` &middot; RCA in ${dur(p.analyzed_at - p.detected_at)}` : ""}${p.resolved_at ? ` &middot; resolved after ${dur(p.resolved_at - p.detected_at)}` : ""}</div></div>
    <div class="row">${p.status !== "analyzing" ? `<button class="btn ghost sm" onclick="reanalyze(${p.id})">Re-run analysis</button>` : ""}
     ${!["resolved", "closed", "rejected"].includes(p.status) ? `<button class="btn ghost sm" onclick="closeInc(${p.id})">Close</button>` : ""}</div></div>
    <div class="grid g4 mt"><div><div class="small muted">Signal</div><b>${esc(s.kind)}</b></div><div><div class="small muted">Observed</div><b class="red">${s.unit === "ratio" ? pct(s.value) : esc(s.value) + " " + esc(s.unit)}</b></div>
     <div><div class="small muted">Threshold (adaptive)</div><b>${s.unit === "ratio" ? pct(s.threshold) : esc(s.threshold) + " " + esc(s.unit)}</b></div><div><div class="small muted">Baseline</div><b>${s.baseline == null ? "-" : s.unit === "ratio" ? pct(s.baseline) : esc(s.baseline)}</b></div></div>
    ${(s.by_version || []).length ? `<div class="small mt8 muted">At detection, failure rate by version: ${s.by_version.map((v) => `v${esc(v.version)} (${esc(v.commit)}) <b class="${v.error_rate > 0.05 ? "red" : ""}">${pct(v.error_rate)}</b>`).join(" &middot; ")}</div>` : ""}
  </div>
  <div class="grid g32">
   <div>
    <div class="card mb"><h3>Root cause</h3>
     ${p.root_cause ? `<div class="rc">${esc(p.root_cause)}</div><p class="muted">${esc(p.summary)}</p>
      <div class="row small"><span class="muted">Confidence</span><div class="conf" style="flex:1"><div style="width:${(p.confidence || 0) * 100}%"></div></div><b>${Math.round((p.confidence || 0) * 100)}%</b></div>
      <div class="small dim mt8">Skill: ${esc(p.skill)} &middot; written by ${esc(p.llm_model)} ${p.llm_ok ? "" : "(template fallback)"} &middot; analysis ${dur((p.analysis_ms || 0) / 1000)}</div>`
     : `<div class="empty">${p.status === "analyzing" || p.status === "open" ? "Agent is investigating... (small CPU model, typically 1-3 min)" : "No analysis"}</div>`}
    </div>
    ${p.runbook ? `<div class="card mb"><h3>Runbook</h3><ol>${(p.runbook || []).map((r) => `<li>${esc(r)}</li>`).join("")}</ol></div>` : ""}
    <div class="card mb"><h3>Agent investigation</h3><div class="timeline">${steps.map(stepHtml).join("") || '<div class="dim">waiting...</div>'}</div></div>
    ${Object.keys(f).length ? `<div class="card"><h3>Correlated evidence</h3><pre>${esc(JSON.stringify(f, null, 2))}</pre></div>` : ""}
   </div>
   <div>
    <div class="card mb"><div class="row between"><h3>Remediation</h3>${p.owner ? `<span class="pill">owner: ${esc(p.owner)}</span>` : ""}</div>
     <div class="small muted mb">The agent dry-runs every fix first. Nothing changes until the owner approves, and the dry run is repeated right before execution.</div>
     ${waiting && p.candidates ? `${p.candidates.map((c, i) => candHtml(c, i)).join("")}
        <label>Approver</label><input id="approver" value="${esc(localStorage.approver || "")}" placeholder="your name">
        <label class="row" style="color:var(--text);margin-top:10px"><input type="checkbox" id="ownerok" style="width:auto"> I am the owner (${esc(p.owner || "unassigned")}) or approved by them</label>
        <label>Comment</label><input id="apcomment" placeholder="optional">
        <div class="row mt"><button class="btn green" id="apbtn" onclick="approve(${p.id})">Approve &amp; execute</button><button class="btn red" onclick="rejectInc(${p.id})">Reject</button></div>`
      : a.label ? `${candHtml(a, -1)}` : '<div class="dim">Pending analysis</div>'}
     ${p.execution ? `<div class="mt small"><div class="kv"><div>Approver</div><div>${esc(p.execution.approver)}${p.execution.owner ? ` for ${esc(p.execution.owner)}` : ""}</div>
       ${p.execution.preflight ? `<div>Pre-flight</div><div class="${p.execution.preflight.ok ? "green" : "red"}">${p.execution.preflight.ok ? "dry run passed again before execution" : "failed"}</div>` : ""}
       ${p.execution.result ? `<div>Result</div><div class="${p.execution.result.ok ? "green" : "red"}">${esc(p.execution.result.detail)}</div>` : ""}
       ${p.execution.rejected ? "<div>Decision</div><div>Rejected</div>" : ""}
       ${p.execution.verification ? `<div>Verification</div><div class="${p.execution.verification.healthy ? "green" : "red"}">${p.execution.verification.healthy ? "metric back to normal" : "still anomalous"}</div>` : ""}</div></div>` : ""}
     ${p.status === "verifying" ? '<div class="small orange mt8">Fix executed - re-checking the signal...</div>' : ""}
    </div>
    <div class="card mb"><h3>Score this RCA</h3>
     <div class="stars" id="stars">${[1, 2, 3, 4, 5].map((n) => `<span class="${n <= starScore ? "on" : ""}" onclick="setStars(${n})">&#9733;</span>`).join("")}</div>
     <label class="row" style="color:var(--text)"><input type="checkbox" id="rcaok" style="width:auto" ${p.rca_correct === 0 ? "" : "checked"}> Root cause was correct</label>
     <label>What should the agent learn?</label><textarea id="fbtext" rows="2">${esc(p.feedback || "")}</textarea>
     <button class="btn mt8" onclick="sendFeedback(${p.id})">Submit feedback</button>
     <div class="small dim mt8">Score 4-5 on a resolved problem saves it as a runbook in incident memory. Low scores become lessons in the next prompt for this skill.</div>
    </div>
    <div class="card mb"><h3>Notifications (Microsoft Teams)</h3>${(p.notifications || []).map((n) => `<div class="small"><b>${esc(n.event)}</b> &middot; ${time(n.ts)} &middot; <span class="dim">${esc(n.status)}</span></div>`).join("") || '<div class="dim small">none</div>'}</div>
    <div class="card"><h3>Explore</h3><a class="btn ghost sm" target="_blank" href="${esc(p.grafana_url)}/explore">Open Grafana Explore</a>
     ${(f.trace_origin_votes || f.self_time_ms) ? '<div class="small dim mt8">Sample traces are listed in the searchTraces step - click one to open the waterfall.</div>' : ""}</div>
   </div>
  </div>`;
  if (!first) {
    for (const [k, v] of Object.entries(keep)) if (v != null && $("#" + k)) $("#" + k).value = v;
    document.querySelectorAll("#view details").forEach((d, i) => { if (openDetails[i]) d.open = true; });
  }
}
problemDetail.refresh = 5000;
function dryHtml(dr) {
  if (!dr) return "";
  return `<div class="dry ${dr.ok ? "pass" : "fail"}"><div class="small"><b class="${dr.ok ? "green" : "red"}">${dr.ok ? "Dry run passed" : "Dry run failed - cannot be approved"}</b> <span class="dim">${time(dr.ts)}</span></div>
    ${(dr.checks || []).map((c) => `<div class="chk"><span class="${c.ok ? "green" : "red"}">${c.ok ? "&#10003;" : "&#10007;"}</span><span><b>${esc(c.name)}</b> <span class="dim">${esc(c.detail)}</span></span></div>`).join("")}
    ${(dr.changes || []).length ? `<div class="small muted mt8">Would change:</div><pre class="small">${esc(dr.changes.join("\n"))}</pre>` : ""}
    ${dr.impact ? `<div class="small mt8"><span class="muted">Impact:</span> ${esc(dr.impact)}</div>` : ""}</div>`;
}
function candHtml(c, i) {
  const ok = !c.dry_run || c.dry_run.ok;
  if (i < 0) return `<div><b>${esc(c.label)}</b>${dryHtml(c.dry_run)}</div>`;
  return `<label class="cand ${i === selCand ? "sel" : ""} ${ok ? "" : "blocked"}" onclick="pickCand(${i}, ${ok})">
    <input type="radio" name="cand" ${i === selCand ? "checked" : ""} ${ok ? "" : "disabled"}><div style="min-width:0;flex:1"><b>${esc(c.label)}</b>${i === 0 && ok ? ' <span class="small green">recommended</span>' : ""}
    <div class="small dim mono">${esc(c.type)} ${esc(JSON.stringify(c.params))}</div>${dryHtml(c.dry_run)}</div></label>`;
}
window.pickCand = (i, ok) => { if (!ok) return toast("This fix failed its dry run"); selCand = i; document.querySelectorAll(".cand").forEach((e, j) => e.classList.toggle("sel", j === i)); };
function stepHtml(s) {
  let body = "";
  if (s.kind === "tool") {
    const samples = s.output?.samples || [];
    body = `<div class="meta mono">${esc(s.title)}(${esc(Object.entries(s.args || {}).map(([k, v]) => `${k}=${JSON.stringify(v)}`).join(", "))}) &middot; ${s.ms} ms</div>
     ${samples.length ? `<div class="small">${samples.map((t) => `<a href="javascript:showTrace('${t.trace_id}')" class="mono">${esc(t.trace_id.slice(0, 10))}</a>`).join(" ")}</div>` : ""}
     <details><summary>output</summary><pre>${esc(JSON.stringify(s.output, null, 2))}</pre></details>`;
  } else if (s.kind === "llm") {
    const m = s.meta || {};
    body = `${(s.findings || []).length ? `<details><summary>findings given to the model</summary><ol class="small">${s.findings.map((x) => `<li>${esc(x)}</li>`).join("")}</ol></details>` : ""}<div class="meta">${esc(m.model || "")} &middot; ${m.ms ? (m.ms / 1000).toFixed(1) + " s" : "running..."} ${m.tokens ? "&middot; " + m.tokens + " tokens" : ""} ${m.error ? `<span class="red">${esc(m.error)}</span>` : ""}</div>
     ${s.output ? `<details><summary>model output</summary><pre>${esc(JSON.stringify(s.output, null, 2))}</pre></details>` : ""}`;
  } else if (s.kind === "guard") {
    body = `<div class="small ${s.rejected ? "orange" : "green"}">${esc(s.detail)}</div>${s.rejected ? `<div class="small dim">Rejected LLM text: "${esc(s.rejected)}"</div>` : ""}`;
  } else if (s.kind === "skill") {
    body = `<div class="small muted">${esc(s.detail)}</div><div class="small dim mono">tools: ${(s.tools || []).map(esc).join(", ")}</div>`;
  } else if (s.kind === "dryrun") {
    body = s.checks ? `<div class="small ${s.ok ? "green" : "red"}">${s.ok ? "passed" : "failed"}: ${(s.checks || []).map((c) => `${c.ok ? "&#10003;" : "&#10007;"} ${esc(c.name)}`).join(" &middot; ")}</div>
      ${s.impact ? `<div class="small dim">${esc(s.impact)}</div>` : ""}` : "";
  } else if (s.kind === "analysis") {
    body = `<div class="small muted">${(s.candidates || []).length} remediation candidate(s) derived from the evidence</div>`;
  } else body = s.detail ? `<div class="small muted">${esc(s.detail)}</div>` : "";
  return `<div class="step ${s.kind}"><div class="t">${esc(s.kind === "tool" ? "Tool call: " + s.title : s.title)}</div><div class="meta">${time(s.ts)}</div>${body}</div>`;
}
window.setStars = (n) => { starScore = n; document.querySelectorAll("#stars span").forEach((e, i) => e.classList.toggle("on", i < n)); };
window.approve = async (id) => {
  const approver = $("#approver").value.trim(); if (!approver) return toast("Enter approver name");
  localStorage.approver = approver;
  if (!$("#ownerok").checked) return toast("Only the owner can approve - tick the owner box");
  $("#apbtn").disabled = true; $("#apbtn").textContent = "Re-running dry run...";
  try { await api(`/api/incidents/${id}/approve`, {method: "POST", body: {approver, action_index: selCand, comment: $("#apcomment").value, owner_confirmed: true}}); toast("Pre-flight passed - executing"); route(); } catch (e) { toast(e.message); route(); }
};
window.rejectInc = async (id) => { const approver = $("#approver").value.trim() || "on-call"; await api(`/api/incidents/${id}/reject`, {method: "POST", body: {approver, comment: $("#apcomment").value}}); toast("Rejected"); route(); };
window.closeInc = async (id) => { await api(`/api/incidents/${id}/close`, {method: "POST"}); route(); };
window.reanalyze = async (id) => { await api(`/api/incidents/${id}/reanalyze`, {method: "POST"}); toast("Re-running analysis"); route(); };
window.sendFeedback = async (id) => {
  if (!starScore) return toast("Pick a score");
  const r = await api(`/api/incidents/${id}/feedback`, {method: "POST", body: {score: starScore, rca_correct: $("#rcaok").checked, comment: $("#fbtext").value}});
  toast(r.message); route();
};

/* ---------------- deployments ---------------- */
async function deploymentsView() {
  crumb("Deployments");
  const rows = await api("/api/deployments");
  $("#view").innerHTML = `<h1>Deployments</h1><p class="sub">Version and commit hash recorded by CI/CD at build and deploy time. The agent uses this history to link an outage to the change behind it.</p>
  <div class="card"><table><tr><th>When</th><th>Service</th><th>Version</th><th>Commit</th><th>Author</th><th>Message</th></tr>
  ${rows.map((d) => `<tr><td class="small">${new Date(d.ts * 1000).toLocaleString()}</td><td><b>${esc(d.service)}</b></td><td>v${esc(d.version)}</td><td class="mono">${esc(d.commit_hash)}</td><td class="small">${esc(d.author)}</td><td class="small">${esc(d.message)}</td></tr>`).join("")}</table></div>`;
}
deploymentsView.refresh = 15000;

/* ---------------- connect ---------------- */
const host = location.hostname;
async function connectApp() {
  crumb("Connect", "App");
  $("#view").innerHTML = `<h1>Connect an application</h1><p class="sub">Register the service and its metadata, point its OpenTelemetry SDK at the platform, and report version and commit from CI.</p>
  <div class="grid g2">
   <div class="card"><h2>1. Service metadata</h2>
    <label>Display name</label><input id="a_name" placeholder="Order API">
    <label>service.name (must match the OTel resource attribute)</label><input id="a_svc" placeholder="order-api">
    <div class="grid g2"><div><label>Language</label><select id="a_lang"><option>python</option><option>java</option><option>nodejs</option><option>go</option><option>dotnet</option></select></div>
     <div><label>Environment</label><input id="a_env" value="production"></div></div>
    <div class="grid g2"><div><label>Owning team (approves fixes)</label><input id="a_team" placeholder="team-orders"></div><div><label>Repository</label><input id="a_repo" placeholder="gitlab.example.com/shop/order-api"></div></div>
    <div class="grid g2"><div><label>Container name (enables restart action)</label><input id="a_cont" placeholder="optional"></div><div><label>Admin URL (enables rollback action)</label><input id="a_admin" placeholder="optional"></div></div>
    <button class="btn mt" onclick="createApp()">Connect app</button>
    <div id="a_result" class="mt"></div>
   </div>
   <div><div class="card mb"><h2>2. Instrument with OpenTelemetry</h2>
    <p class="small muted">Set these on the service. Traces and logs go to the platform's collector; RED metrics are derived automatically.</p>
    <pre id="otelenv">OTEL_SERVICE_NAME=&lt;service.name&gt;
OTEL_EXPORTER_OTLP_ENDPOINT=http://${esc(host)}:4318
OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
OTEL_TRACES_EXPORTER=otlp
OTEL_LOGS_EXPORTER=otlp
OTEL_RESOURCE_ATTRIBUTES=deployment.environment=production</pre>
    <p class="small muted mt8">Stamp each request span with <span class="mono">app.version</span> and <span class="mono">app.commit</span> so failures can be pinned to a commit.</p></div>
    <div class="card"><h2>3. Report deployments from CI</h2>
    <pre>curl -X POST http://${esc(host)}:8080/api/deployments \\
  -H 'Content-Type: application/json' \\
  -d '{"service":"order-api","version":"'$CI_COMMIT_TAG'",
       "commit":"'$CI_COMMIT_SHORT_SHA'","author":"'$GITLAB_USER_LOGIN'",
       "message":"'$CI_COMMIT_TITLE'"}'</pre></div></div>
  </div>
  <div class="card mt"><h2>Connected applications</h2><div id="applist">loading...</div></div>`;
  listApps();
}
async function listApps() {
  const apps = await api("/api/apps");
  $("#applist").innerHTML = `<table><tr><th>Name</th><th>service.name</th><th>Team</th><th>Data</th><th></th></tr>${apps.map((a) => `<tr><td>${esc(a.name)}</td><td class="mono">${esc(a.service_name)}</td><td>${esc(a.team)}</td>
   <td><span class="dot ${a.status}"></span> ${a.status === "no-data" ? "waiting for telemetry" : "receiving"}</td>
   <td><button class="btn ghost sm" onclick="verifyApp('${esc(a.service_name)}')">Verify</button> <button class="btn ghost sm" onclick="delApp(${a.id})">Remove</button></td></tr>`).join("")}</table>`;
}
window.createApp = async () => {
  const body = {name: $("#a_name").value, service_name: $("#a_svc").value.trim(), language: $("#a_lang").value, environment: $("#a_env").value,
    team: $("#a_team").value, repo: $("#a_repo").value, container: $("#a_cont").value, admin_url: $("#a_admin").value};
  if (!body.name || !body.service_name) return toast("Name and service.name are required");
  try { await api("/api/apps", {method: "POST", body}); toast("App connected - anomaly detection is now active for it"); $("#otelenv").textContent = $("#otelenv").textContent.replace("<service.name>", body.service_name); listApps(); verifyApp(body.service_name); } catch (e) { toast(e.message); }
};
window.verifyApp = async (svc) => {
  const v = await api(`/api/apps/${svc}/verify`);
  const ok = (b) => b ? '<span class="green">received</span>' : '<span class="orange">not yet</span>';
  $("#a_result").innerHTML = `<div class="card"><b>${esc(svc)}</b> - metrics ${ok(v.metrics)} &middot; logs ${ok(v.logs)} &middot; traces ${ok(v.traces)}</div>`;
  toast(`${svc}: metrics ${v.metrics ? "ok" : "-"}, logs ${v.logs ? "ok" : "-"}, traces ${v.traces ? "ok" : "-"}`);
};
window.delApp = async (id) => { await api(`/api/apps/${id}`, {method: "DELETE"}); listApps(); };

async function connectInfra() {
  crumb("Connect", "Infrastructure");
  $("#view").innerHTML = `<h1>Connect infrastructure</h1><p class="sub">Install the host agent (node_exporter), then register the host. Prometheus picks it up within 15 s - no restart.</p>
  <div class="grid g2">
   <div class="card"><h2>1. Install the agent on the host</h2>
    <pre>docker run -d --name node-exporter --restart unless-stopped \\
  --net host --pid host -v /:/host:ro,rslave \\
  prom/node-exporter:v1.9.1 --path.rootfs=/host

# allow only the AIOps platform to scrape it
sudo ufw allow from ${esc(host)} to any port 9100 proto tcp</pre>
    <p class="small muted mt8">For VMs without Docker use the node_exporter binary + systemd. Kubernetes nodes: deploy it as a DaemonSet.</p></div>
   <div class="card"><h2>2. Register the host</h2>
    <label>Host name</label><input id="h_name" placeholder="db-01">
    <label>Agent address (host:port)</label><input id="h_addr" placeholder="10.4.82.30:9100">
    <div class="grid g2"><div><label>OS</label><input id="h_os" value="Ubuntu"></div><div><label>Environment</label><input id="h_env" value="production"></div></div>
    <label>Role label</label><input id="h_role" placeholder="database">
    <button class="btn mt" onclick="createHost()">Connect host</button></div>
  </div>
  <div class="card mt"><h2>Connected hosts</h2><div id="hostlist">loading...</div></div>`;
  listHosts();
}
async function listHosts() {
  const hs = await api("/api/hosts");
  $("#hostlist").innerHTML = `<table><tr><th>Name</th><th>Address</th><th>Status</th><th>CPU</th><th>Mem</th><th></th></tr>${hs.map((h) => `<tr><td><b>${esc(h.name)}</b></td><td class="mono">${esc(h.address)}</td>
   <td><span class="dot ${h.status}"></span> ${h.status === "no-data" ? "waiting for first scrape" : h.status}</td><td>${num(h.cpu)}%</td><td>${num(h.mem)}%</td>
   <td><button class="btn ghost sm" onclick="delHost(${h.id})">Remove</button></td></tr>`).join("")}</table>`;
}
window.createHost = async () => {
  const body = {name: $("#h_name").value.trim(), address: $("#h_addr").value.trim(), os: $("#h_os").value, environment: $("#h_env").value,
    labels: $("#h_role").value ? {role: $("#h_role").value} : {}};
  if (!body.name || !body.address) return toast("Name and address are required");
  try { await api("/api/hosts", {method: "POST", body}); toast("Host registered - Prometheus will scrape it within 15 s"); listHosts(); } catch (e) { toast(e.message); }
};
window.delHost = async (id) => { await api(`/api/hosts/${id}`, {method: "DELETE"}); listHosts(); };

/* ---------------- agentic AI ---------------- */
async function skillsView() {
  crumb("Agentic AI", "Skills & Scoring");
  const sk = await api("/api/skills");
  $("#view").innerHTML = `<h1>Skills &amp; scoring</h1><p class="sub">The orchestrator classifies each problem and picks one skill. A skill is a set of read-only tools; engineers' scores feed back into it.</p>
  <div class="grid g2">${sk.map((s) => `<div class="card"><div class="row between"><h2>${esc(s.name)}</h2><span class="badge b-info">${esc(s.category)}</span></div>
   <p class="muted small">${esc(s.description)}</p><div class="small mono dim">${s.tools.map(esc).join(" &middot; ")}</div>
   <div class="grid g4 mt"><div><div class="small muted">Runs</div><b>${s.runs}</b></div><div><div class="small muted">Avg score</div><b>${s.avg_score ?? "-"}</b></div>
    <div><div class="small muted">RCA accuracy</div><b>${s.accuracy == null ? "-" : Math.round(s.accuracy * 100) + "%"}</b></div><div><div class="small muted">Avg analysis</div><b>${s.avg_analysis_s ?? "-"} s</b></div></div>
   ${s.lessons.length ? `<div class="mt small"><div class="muted">Lessons injected into the next prompt:</div>${s.lessons.map((l) => `<div>- ${esc(l)}</div>`).join("")}</div>` : ""}</div>`).join("")}</div>`;
}
async function runbooksView() {
  crumb("Agentic AI", "Runbook Memory");
  const rbs = await api("/api/runbooks");
  $("#view").innerHTML = `<h1>Runbook memory</h1><p class="sub">Approved, well-scored analyses are kept here. When a new problem matches a signature, the agent reuses the runbook instead of generating a fresh RCA.</p>
  ${rbs.length ? rbs.map((r) => `<div class="card mb"><div class="row between"><div><b>RB-${r.id}</b> ${esc(r.title)} ${r.enabled ? "" : '<span class="badge b-closed">disabled</span>'}</div>
   <button class="btn ghost sm" onclick="toggleRb(${r.id})">${r.enabled ? "Disable" : "Enable"}</button></div>
   <div class="small mono dim mt8">${esc(r.signature)}</div><p>${esc(r.root_cause)}</p><ol class="small">${(r.runbook || []).map((x) => `<li>${esc(x)}</li>`).join("")}</ol>
   <div class="small muted">Action: ${esc(r.action?.label)} &middot; used ${r.uses}x &middot; avg score ${r.score_n ? (r.score_sum / r.score_n).toFixed(1) : "-"} &middot; from <a href="#/problems/${r.source_incident}">P-${r.source_incident}</a></div></div>`).join("")
  : '<div class="card empty">Empty. Resolve a problem and score it 4-5 to save its runbook.</div>'}`;
}
window.toggleRb = async (id) => { await api(`/api/runbooks/${id}/toggle`, {method: "POST"}); runbooksView(); };
async function notificationsView() {
  crumb("Agentic AI", "Notifications");
  const rows = await api("/api/notifications");
  $("#view").innerHTML = `<h1>Notifications</h1><p class="sub">Everything pushed to Microsoft Teams (configure the webhook in Settings).</p>
  <div class="card"><table><tr><th>When</th><th>Problem</th><th>Event</th><th>Delivery</th></tr>${rows.map((n) => `<tr><td class="small">${new Date(n.ts * 1000).toLocaleString()}</td>
   <td>${n.incident_id ? `<a href="#/problems/${n.incident_id}">P-${n.incident_id}</a>` : "test"}</td><td>${esc(n.event)}</td><td class="small">${esc(n.status)}</td></tr>`).join("")}</table></div>`;
}
notificationsView.refresh = 10000;

/* ---------------- chaos ---------------- */
const SCEN = [
  ["bad_deploy", "Bad deployment (payment v1.3.0)", "CI deploys a new payment commit with a discount bug. ~45% of charges fail; checkout and frontend fail too.",
    "Service skill: traces point to payment, the failure rate is isolated to the new version/commit, deploy history matches. Recommends rollback to v1.2.0."],
  ["slow_db", "Connection pool exhaustion (inventory)", "Inventory queries take ~1.6 s and the pool saturates, so every page and checkout slows down.",
    "Latency skill: slow-trace self-time puts it in inventory, warning logs show pool exhaustion. Recommends restarting inventory."],
  ["cpu_hog", "CPU saturation (runaway batch job)", "A batch job inside the payment container spins 3 cores for 10 minutes and the host CPU saturates.",
    "Infrastructure skill: host metrics plus per-container CPU find the payment container; logs show the batch job. Recommends a restart."],
  ["brute_force", "Credential stuffing (frontend)", "One IP hammers /api/login through the edge firewall with failed passwords for 4 minutes.",
    "Security skill: firewall logs and app logs agree on one source IP. Dry run validates the new firewall rule with nginx -t, then asks the owner to block it."],
  ["instance_fault", "One instance behind the LB breaks (frontend-b)", "frontend-b loses its session cache and fails half its requests; frontend-a stays healthy.",
    "Service skill reads the load balancer logs: the 5xx all come from one upstream. Dry run confirms frontend-a can carry the traffic, so it proposes restarting only frontend-b."],
];
async function chaosView() {
  crumb("Demo", "Chaos Scenarios");
  $("#view").innerHTML = `<h1>Chaos scenarios</h1><p class="sub">Inject a realistic fault into the demo shop and watch it go Observe &rarr; Identify anomaly &rarr; Investigate &rarr; Summarize &amp; recommend &rarr; Approve &rarr; Improve score.
   Detection takes about 30-45 s; the CPU model needs another 1-3 min for the RCA.</p>
  <div class="grid g2">${SCEN.map(([id, t, what, expect]) => `<div class="card scen"><h2>${t}</h2><div class="small"><span class="muted">What happens:</span> ${what}</div>
   <div class="small"><span class="muted">Expected agent behaviour:</span> ${expect}</div><div><button class="btn" onclick="chaos('${id}')">Inject</button></div></div>`).join("")}</div>
  <div class="card mt row between"><div><b>Reset faults</b><div class="small muted">Clears injected errors/latency, the blocklist and the attack (does not roll back versions).</div></div><button class="btn ghost" onclick="chaos('reset')">Reset</button></div>`;
}
window.chaos = async (id) => { try { await api(`/api/chaos/${id}`, {method: "POST"}); toast(id === "reset" ? "Faults cleared" : "Fault injected - watch Problems"); } catch (e) { toast(e.message); } };

/* ---------------- settings ---------------- */
async function settingsView() {
  crumb("Settings");
  const d = await api("/api/settings"), s = d.settings;
  const f = (k, l, hint = "") => `<label>${l}</label><input id="s_${k}" value="${esc(s[k])}">${hint ? `<div class="small dim">${hint}</div>` : ""}`;
  $("#view").innerHTML = `<h1>Settings</h1><p class="sub">Platform configuration. No login in this PoC.</p>
  <div class="grid g2">
   <div class="card"><h2>Microsoft Teams</h2>${f("teams_webhook", "Incoming webhook / Workflows URL", "Adaptive Card is posted when a problem is detected, RCA is ready, and when it resolves.")}
    <div class="row mt"><button class="btn ghost" onclick="testTeams()">Send test</button></div>
    <h2 class="mt">Agentic AI</h2><label>LLM model (Ollama)</label><select id="s_llm_model">${(d.llm.models || [s.llm_model]).map((m) => `<option ${m === s.llm_model ? "selected" : ""}>${esc(m)}</option>`).join("")}</select>
    <div class="small dim">Ollama: ${d.llm.up ? "online" : "offline"}. Pull more with <span class="mono">docker exec ollama ollama pull qwen2.5:3b</span></div>
    <label>Auto-analyze new problems</label><select id="s_auto_analyze"><option value="1" ${s.auto_analyze === "1" ? "selected" : ""}>yes</option><option value="0" ${s.auto_analyze === "0" ? "selected" : ""}>no</option></select>
    ${f("verify_after_s", "Verify fix after (s)")}</div>
   <div class="card"><h2>Detection thresholds (floors for the adaptive baseline)</h2>
    ${f("err_threshold", "Failure rate (0-1)")}${f("p95_threshold_ms", "Response time p95 (ms)")}${f("cpu_threshold", "Host CPU %")}${f("mem_threshold", "Host memory %")}
    ${f("disk_threshold", "Host disk %")}${f("auth_fail_per_min", "Failed logins per minute")}</div>
  </div><button class="btn mt" onclick="saveSettings()">Save settings</button>`;
}
window.saveSettings = async () => {
  const body = {};
  document.querySelectorAll("[id^=s_]").forEach((e) => body[e.id.slice(2)] = e.value);
  await api("/api/settings", {method: "PUT", body}); toast("Saved");
};
window.testTeams = async () => { await saveSettings(); const r = await api("/api/settings/test-teams", {method: "POST"}); toast("Teams: " + r.status); };

/* ---------------- modal ---------------- */
function openModal(html) { $("#modal-body").innerHTML = html; $("#modal").classList.remove("hidden"); }
window.closeModal = () => $("#modal").classList.add("hidden");
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });
window.showTrace = showTrace;

setInterval(async () => { try { if ((location.hash || "#/") !== "#/") status(await api("/api/overview")); } catch (e) {} }, 20000);
api("/api/overview").then(status).catch(() => {});
route();
