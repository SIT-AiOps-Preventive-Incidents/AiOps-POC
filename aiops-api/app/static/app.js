/* AIOps One - single-page UI (no build step). Light "Azure x iOS" design. */
const $ = (s) => document.querySelector(s);
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"}[c]));
const api = async (path, opts = {}) => {
  const r = await fetch(path, {headers: {"Content-Type": "application/json"}, ...opts, body: opts.body ? JSON.stringify(opts.body) : undefined});
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.detail || r.statusText);
  return data;
};
const toast = (m) => { const t = $("#toast"); t.textContent = m; t.style.display = "block"; clearTimeout(t._h); t._h = setTimeout(() => t.style.display = "none", 3200); };
const pct = (v, d = 1) => v == null ? "-" : (v * 100).toFixed(d) + "%";
const num = (v, d = 1) => v == null ? "-" : Number(v).toFixed(d);
const ms = (v) => v == null ? "-" : v >= 1000 ? (v / 1000).toFixed(2) + " s" : Math.round(v) + " ms";
const ago = (ts) => { if (!ts) return "-"; const s = Date.now() / 1000 - ts; if (s < 60) return "just now"; if (s < 3600) return Math.round(s / 60) + " min ago"; if (s < 86400) return Math.round(s / 3600) + " h ago"; return Math.round(s / 86400) + " d ago"; };
const dur = (s) => s == null || isNaN(s) ? "-" : s < 60 ? Math.round(s) + " s" : s < 3600 ? Math.floor(s / 60) + " min " + Math.round(s % 60) + " s" : (s / 3600).toFixed(1) + " h";
const hhmm = (ts) => ts ? new Date(ts * 1000).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"}) : "";
const hhmmss = (ts) => ts ? new Date(ts * 1000).toLocaleTimeString() : "-";
const store = {get: (k, d = "") => { try { return localStorage.getItem(k) ?? d; } catch { return d; } }, set: (k, v) => { try { localStorage.setItem(k, v); } catch {} }};

/* ---------- icons: Microsoft Fluent UI System Icons (MIT) + real brand logos (Devicon MIT, Simple Icons CC0) ---------- */
const FI = {home: "home", alert: "warning", map: "flowchart", cube: "cube", laptop: "laptop", server: "server", plus: "add_circle",
  sparkle: "sparkle", book: "book", bell: "alert", branch: "branch", bolt: "flash", gear: "settings", check: "checkmark", x: "dismiss",
  chev: "chevron_right", back: "chevron_left", cpu: "developer_board", disk: "hard_drive", shield: "shield", clock: "clock", wand: "wand",
  wrench: "wrench", search: "search", list: "list", globe: "globe", pulse: "pulse", copy: "copy"};
const fiUrl = (k, filled) => `/static/icons/f/${FI[k] || k}_${filled ? "filled" : "regular"}.svg`;
const icon = (k, filled = false, size) => `<span class="fi" aria-hidden="true" style="--i:url('${fiUrl(k, filled === true)}')${size ? `;width:${size}px;height:${size}px` : ""}"></span>`;
const chev = `<span class="fi chev" aria-hidden="true" style="--i:url('${fiUrl("chev")}')"></span>`;
const ibox = (k, bg) => `<span class="ic" style="background:${bg}">${icon(k, true)}</span>`;
const brand = (k, size = 20, alt = "") => k ? `<img class="blogo" src="/static/icons/b/${k}.svg" width="${size}" height="${size}" alt="${esc(alt)}">` : "";
const langOf = (l) => { l = (l || "").toLowerCase(); return /python/.test(l) ? "python" : /node|javascript|typescript/.test(l) ? "node" : /java/.test(l) ? "java"
  : /net|c#|csharp/.test(l) ? "dotnet" : /nginx/.test(l) ? "nginx" : /docker/.test(l) ? "docker" : null; };
const osOf = (o) => /darwin|mac/i.test(o || "") ? "apple" : /linux|ubuntu|debian|centos|rhel/i.test(o || "") ? "linux" : null;
/* app-icon style tile: real logo on white, with a status dot in the corner */
const ltile = (logo, fallbackIcon, status) => `<span class="ic logo">${logo ? brand(logo, 20) : icon(fallbackIcon, false, 18)}${status ? `<span class="sdot ${status}"></span>` : ""}</span>`;

/* ---------- status vocabulary ---------- */
const ST = {
  open: ["New", "p-warn"], analyzing: ["AI investigating", "p-ai"], awaiting_approval: ["Needs approval", "p-ai"],
  remediating: ["Applying fix", "p-info"], verifying: ["Checking fix", "p-info"], resolved: ["Resolved", "p-ok"],
  rejected: ["Rejected", ""], closed: ["Closed", ""], remediation_failed: ["Fix didn't work", "p-bad"],
};
const pill = (s) => `<span class="pill ${ST[s]?.[1] || ""}">${esc(ST[s]?.[0] || s)}</span>`;
const sevPill = (s) => s === "critical" ? '<span class="pill p-solid-bad">Critical</span>' : s === "major" ? '<span class="pill p-solid-warn">Major</span>' : `<span class="pill">${esc(s || "info")}</span>`;
const KIND_IC = {error_rate: ["alert", "var(--bad-dot)"], latency: ["clock", "var(--warn-dot)"], host_cpu: ["cpu", "var(--c-purple)"],
  host_mem: ["cpu", "var(--c-purple)"], host_disk: ["disk", "var(--c-purple)"], host_down: ["server", "var(--bad-dot)"], auth_bruteforce: ["shield", "var(--c-teal)"]};
const kindBox = (k) => ibox(...(KIND_IC[k] || ["alert", "var(--text-3)"]));
const ACTIVE = ["open", "analyzing", "remediating", "verifying", "remediation_failed"];
const problemPill = '<span class="pill p-bad">Problem</span>';

/* ---------- navigation ---------- */
const MENU = [
  ["", [["#/", "Home", "home"], ["#/problems", "Problems", "alert"], ["#/map", "Service Map", "map"], ["#/services", "Services", "cube"], ["#/infra", "Computers & Servers", "server"], ["#/connect", "Connect", "plus"]]],
  ["AI", [["#/skills", "Skills & Scores", "sparkle"], ["#/runbooks", "Runbooks", "book"], ["#/notifications", "Notifications", "bell"]]],
  ["More", [["#/deployments", "Deployments", "branch"], ["#/chaos", "Demo Scenarios", "bolt"], ["#/settings", "Settings", "gear"]]],
];
let badge = 0;
function renderMenu() {
  const h = location.hash || "#/";
  $("#menu").innerHTML = MENU.map(([sec, items]) => (sec ? `<div class="navsec">${sec}</div>` : "") + items.map(([href, label, ic]) => {
    const on = href === "#/" ? h === "#/" || h === "" : h.startsWith(href);
    return `<a class="navitem ${on ? "active" : ""}" href="${href}">${icon(ic)}<span>${label}</span>${href === "#/problems" && badge ? `<span class="cnt">${badge}</span>` : ""}</a>`;
  }).join("")).join("");
}
function statusBar(d) {
  badge = d.kpi.open;
  renderMenu();
  const l = d.llm, det = d.detector, fresh = det.ts && Date.now() / 1000 - det.ts < 60;
  $("#chips").innerHTML = `<span class="chip"><span class="dot ${fresh ? "healthy" : "offline"}"></span>${fresh ? "Monitoring live" : "Detector starting"}</span>
    <span class="chip">${brand("ollama", 14, "Ollama")}<span class="dot ${l.up && l.models.includes(l.active) ? "healthy" : "problem"}"></span>${esc(l.up ? l.active : "AI offline")}</span>`;
  $("#grafana").href = d.grafana_url;
  $("#navfoot").innerHTML = `<span>${d.services.length} services · ${d.hosts.length} computers</span><span class="stack-logos" title="OpenTelemetry, Prometheus, Grafana">${brand("otel", 16, "OpenTelemetry")}${brand("prometheus", 16, "Prometheus")}${brand("grafana", 16, "Grafana")}<span>Powered by open source</span></span>`;
}

/* ---------- router ---------- */
let timer = null, lastKey = "";
const routes = [
  [/^#?\/?$/, home], [/^#\/problems$/, problems], [/^#\/problems\/(\d+)$/, problemDetail], [/^#\/map$/, serviceMap],
  [/^#\/services$/, services], [/^#\/services\/(.+)$/, serviceDetail], [/^#\/infra$/, infra], [/^#\/infra\/(.+)$/, hostDetail],
  [/^#\/connect$/, connectHub], [/^#\/connect\/computer$/, connectComputer], [/^#\/connect\/service$/, connectService],
  [/^#\/connect\/(app|infra)$/, () => { location.hash = "#/connect"; }],
  [/^#\/deployments$/, deploymentsView], [/^#\/skills$/, skillsView], [/^#\/runbooks$/, runbooksView],
  [/^#\/notifications$/, notificationsView], [/^#\/chaos$/, chaosView], [/^#\/settings$/, settingsView],
];
async function route() {
  clearInterval(timer); lastKey = ""; document.body.classList.remove("navopen");
  renderMenu();
  const h = location.hash || "#/";
  for (const [re, fn] of routes) {
    const m = h.match(re);
    if (!m) continue;
    const run = async (first) => { try { await fn(...m.slice(1), first); } catch (e) { if (first) $("#view").innerHTML = `<div class="page"><div class="card mt bad">${esc(e.message)}</div></div>`; } };
    $("#view").scrollTop = 0;
    await run(true);
    if (fn.refresh) timer = setInterval(() => { if (!document.hidden) run(false); }, fn.refresh);
    return;
  }
  $("#view").innerHTML = '<div class="page"><div class="empty">Page not found</div></div>';
}
window.addEventListener("hashchange", route);
/* Re-render only when the data changed, so typing and open sections survive auto-refresh. */
const changed = (obj) => { const k = JSON.stringify(obj); if (k === lastKey) return false; lastKey = k; return true; };
const typing = () => ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);
const head = (title, sub = "", right = "", back = null) => `<div class="page-head"><div>${back ? `<a class="back" href="${back[0]}">${icon("back", false, 18)}${esc(back[1])}</a>` : ""}<h1 class="lt">${title}</h1>${sub ? `<p class="sub">${sub}</p>` : ""}</div><div class="chips">${right}</div></div>`;

/* ---------- charts ---------- */
function chartCard(points, {color = "var(--c-blue)", h = 96, fmt = (v) => num(v, 2), title = ""} = {}) {
  const pts = (points || []).filter((p) => p[1] != null);
  if (pts.length < 2) return `<div class="card chart-card"><div class="row-h"><h3>${esc(title)}</h3></div><div class="empty">Waiting for data</div></div>`;
  const W = 600, xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), ymax = Math.max(...ys) * 1.15 || 1;
  const X = (x) => ((x - x0) / (x1 - x0 || 1)) * W, Y = (y) => h - 2 - (y / ymax) * (h - 10);
  const line = pts.map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" ");
  const id = "g" + Math.random().toString(36).slice(2, 8), last = pts[pts.length - 1];
  return `<div class="card chart-card"><div class="row-h"><h3>${esc(title)}</h3><span class="v">${fmt(last[1])}</span></div>
    <svg class="chart" viewBox="0 0 ${W} ${h}" preserveAspectRatio="none" style="height:${h}px" role="img" aria-label="${esc(title)} over the last hour">
    <defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1"><stop offset="0" style="stop-color:${color};stop-opacity:.22"/><stop offset="1" style="stop-color:${color};stop-opacity:0"/></linearGradient></defs>
    <line x1="0" x2="${W}" y1="${Y(ymax / 1.15)}" y2="${Y(ymax / 1.15)}" style="stroke:var(--sep)" stroke-dasharray="3 4"/>
    <polygon points="0,${h} ${line} ${W},${h}" fill="url(#${id})"/>
    <polyline points="${line}" fill="none" style="stroke:${color}" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round"/></svg>
    <div class="row-h small dim"><span>${hhmm(x0)}</span><span>peak ${fmt(ymax / 1.15)}</span><span>${hhmm(x1)}</span></div></div>`;
}
const barColor = (v, warn = 70, crit = 90) => v == null ? "var(--gray-dot)" : v >= crit ? "var(--bad-dot)" : v >= warn ? "var(--warn-dot)" : "var(--ok-dot)";
const meter = (label, v, warn, crit) => `<div class="meter"><span class="muted">${label}</span><div class="bar"><div style="width:${Math.min(v || 0, 100)}%;background:${barColor(v, warn, crit)}"></div></div><span class="p">${v == null ? "-" : Math.round(v) + "%"}</span></div>`;

/* ---------- rows ---------- */
const svcRow = (s) => `<a class="li" href="#/services/${esc(s.service || s.service_name)}">${ltile(langOf(s.language || (s.kind === "network" ? "nginx" : "")), "cube", s.status)}
  <div class="tx"><div class="t">${esc(s.name || s.service)}</div><div class="s">${s.version ? `v${esc(s.version)} · ` : ""}${s.status === "no-data" ? "waiting for data" : `${num(s.rps, 1)} req/s · p95 ${ms(s.p95_ms)}`}</div></div>
  <span class="acc ${s.error_rate > 0.05 ? "bad" : ""}">${s.problem_id ? problemPill : s.error_rate == null ? "" : pct(s.error_rate) + " errors"}</span>${chev}</a>`;
const hostLine = (h) => h.status === "offline" ? "Offline" : h.status === "no-data" ? "Waiting for first data" : `CPU ${Math.round(h.cpu)}% · Memory ${Math.round(h.mem)}% · Disk ${Math.round(h.disk)}%`;
const hostBox = (h) => ltile(osOf(h.os), h.kind === "workstation" ? "laptop" : "server", h.status);
const hostRow = (h) => `<a class="li" href="#/infra/${esc(h.name)}">${hostBox(h)}<div class="tx"><div class="t">${esc(h.name)}</div><div class="s">${hostLine(h)}</div></div>
  <span class="acc">${h.problem_id ? problemPill : h.status === "healthy" ? '<span class="dot healthy"></span>' : ""}</span>${chev}</a>`;
const probRow = (p) => `<a class="li" href="#/problems/${p.id}">${kindBox(p.kind)}<div class="tx"><div class="t">${esc(p.title)}</div>
  <div class="s">P-${p.id} · ${esc(p.entity)} · ${ago(p.detected_at)}${p.owner ? " · " + esc(p.owner) : ""}</div>${p.root_cause ? `<div class="s2">${esc(p.root_cause)}</div>` : ""}</div>
  <span class="acc">${pill(p.status)}</span>${chev}</a>`;

/* ======================= HOME ======================= */
async function home() {
  const d = await api("/api/overview");
  statusBar(d);
  if (!changed(d)) return;
  const k = d.kpi, need = d.open_problems.filter((p) => p.status === "awaiting_approval"), other = d.open_problems.filter((p) => p.status !== "awaiting_approval");
  const heroCls = need.length ? "wait" : other.length ? "bad" : "good";
  const heroTitle = need.length ? `${need.length} fix${need.length > 1 ? "es are" : " is"} waiting for your approval` : other.length ? `${other.length} problem${other.length > 1 ? "s are" : " is"} being investigated` : "Everything is running normally";
  const heroSub = `${d.services.length} services and ${d.hosts.length} computers are monitored. Last check ${d.detector.ts ? ago(d.detector.ts) : "-"}.`;
  $("#view").innerHTML = `<div class="page">${head("Home")}
  <div class="hero ${heroCls}"><div class="big">${icon(need.length ? "wand" : other.length ? "alert" : "check", true)}</div><div style="flex:1;min-width:0"><h2>${heroTitle}</h2><div class="muted">${heroSub}</div></div>
    ${need.length || other.length ? '<a class="btn" href="#/problems">Review</a>' : '<a class="btn tint" href="#/connect">Connect more</a>'}</div>
  <div class="grid g4 mt">
    <div class="tile"><div class="l">Open problems</div><div class="v ${k.open ? "bad" : ""}">${k.open}</div><div class="h">${k.total} in total</div></div>
    <div class="tile"><div class="l">Waiting for approval</div><div class="v">${k.awaiting_approval}</div><div class="h">fixes already dry-run</div></div>
    <div class="tile"><div class="l">Time to detect</div><div class="v">${dur(k.mttd_s)}</div><div class="h">average</div></div>
    <div class="tile"><div class="l">Time to fix</div><div class="v">${dur(k.mttr_s)}</div><div class="h">detected to verified</div></div>
  </div>
  ${d.open_problems.length ? `<div class="sec-h row"><span>Open problems</span><a href="#/problems">See all</a></div><div class="list">${d.open_problems.map(probRow).join("")}</div>` : ""}
  <div class="grid g2">
    <div><div class="sec-h row"><span>Services</span><a href="#/services">See all</a></div><div class="list">${d.services.map(svcRow).join("") || '<div class="empty">No services yet</div>'}</div></div>
    <div><div class="sec-h row"><span>Computers & servers</span><a href="#/infra">See all</a></div><div class="list">${d.hosts.map(hostRow).join("") || '<div class="empty">No computers yet</div>'}</div>
      <div class="sec-h row"><span>Quick actions</span></div>
      <div class="list">
        <a class="li" href="#/connect/service">${ibox("cube", "var(--blue)")}<div class="tx"><div class="t">Connect a service</div><div class="s">Send traces and logs from your app</div></div>${chev}</a>
        <a class="li" href="#/connect/computer">${ibox("laptop", "var(--c-purple)")}<div class="tx"><div class="t">Connect a computer</div><div class="s">One command for macOS or Linux</div></div>${chev}</a>
        <a class="li" href="#/map">${ibox("map", "var(--c-teal)")}<div class="tx"><div class="t">Open the service map</div><div class="s">See every hop a request takes</div></div>${chev}</a>
        <a class="li" href="#/chaos">${ibox("bolt", "var(--warn-dot)")}<div class="tx"><div class="t">Try a demo problem</div><div class="s">Break something and watch the AI fix it</div></div>${chev}</a>
      </div></div>
  </div></div>`;
}
home.refresh = 10000;

/* ======================= PROBLEMS ======================= */
async function problems() {
  const rows = await api("/api/incidents");
  if (!changed(rows)) return;
  const need = rows.filter((p) => p.status === "awaiting_approval"), act = rows.filter((p) => ACTIVE.includes(p.status)), done = rows.filter((p) => ["resolved", "rejected", "closed"].includes(p.status)).slice(0, 30);
  const sec = (t, list, empty) => `<div class="sec-h">${t}</div><div class="list">${list.length ? list.map(probRow).join("") : `<div class="empty">${empty}</div>`}</div>`;
  $("#view").innerHTML = `<div class="page">${head("Problems", "The AI investigates every problem. Fixes are dry-run first and only applied after the owner approves.")}
    ${sec(`Needs your approval (${need.length})`, need, "Nothing is waiting for approval")}
    ${sec(`In progress (${act.length})`, act, "No problems are being worked on")}
    ${sec("Recently closed", done, "No history yet. Try a <a href='#/chaos'>demo problem</a>.")}</div>`;
}
problems.refresh = 6000;

let selCand = 0, starScore = 0, ownerOk = false;
const TLI = {tool: ["search", "var(--blue)"], llm: ["sparkle", "var(--ai-dot)"], skill: ["wand", "var(--warn-dot)"], analysis: ["list", "var(--c-teal)"],
  memory: ["book", "var(--c-teal)"], dryrun: ["wrench", "var(--c-teal)"], guard: ["shield", "var(--ok-dot)"], done: ["check", "var(--ok-dot)"], info: ["sparkle", "var(--text-3)"]};
function tlRow(x) {
  const [ic, c] = TLI[x.kind] || TLI.info, t = x.ms ?? x.meta?.ms;
  const data = x.output ?? (x.checks ? {checks: x.checks, changes: x.changes, impact: x.impact} : x.facts ? {facts: x.facts, candidates: x.candidates} : null);
  const body = (x.detail ? `<div class="small muted">${esc(x.detail)}</div>` : "") + (x.rejected ? `<div class="small dim">AI wrote: "${esc(x.rejected)}"</div>` : "") +
    (data ? `<details class="mini"><summary>details</summary><pre class="out">${esc(JSON.stringify(data, null, 2))}</pre></details>` : "");
  return `<div class="tl-row" style="align-items:flex-start"><span class="ic" style="background:${c}">${icon(ic, true)}</span><div style="flex:1;min-width:0"><div>${esc(x.kind === "tool" ? x.title + "()" : x.title)}</div>${body}</div><span class="small dim">${t != null ? (t / 1000).toFixed(1) + " s" : ""}</span></div>`;
}
async function problemDetail(id, first) {
  if (first) { selCand = 0; starScore = 0; ownerOk = false; }
  if (!first && typing()) return;
  const p = await api(`/api/incidents/${id}`);
  if (first) starScore = p.score || 0;
  if (!changed({p, selCand})) return;
  const keep = {approver: $("#approver")?.value, apcomment: $("#apcomment")?.value, fbtext: $("#fbtext")?.value};
  const openD = [...document.querySelectorAll("#view details")].map((d) => d.open);
  const s = p.signal || {}, ex = p.execution || {};
  const waiting = ["awaiting_approval", "remediation_failed"].includes(p.status);
  const investigating = ["open", "analyzing"].includes(p.status);
  const fixedTs = ex.result?.ok ? ex.ts : null;
  const steps = [["Detected", p.detected_at, true], ["Analyzed", p.analyzed_at, !!p.analyzed_at], ["Approved", p.approved_at, !!p.approved_at],
    ["Fixed", fixedTs, !!fixedTs], ["Verified", p.status === "resolved" ? p.resolved_at : null, p.status === "resolved"]];
  const nowIdx = steps.findIndex((x) => !x[2]);
  const failed = p.status === "remediation_failed" || p.status === "rejected";
  const stepper = `<div class="stepper" aria-label="Progress">${steps.map(([l, t, done], i) => {
    const cls = done ? "done" : i === nowIdx ? (failed ? "fail" : "now") : "";
    return `<div class="stp ${cls}"><div class="c">${done ? icon("check") : cls === "fail" ? icon("x") : i + 1}</div><div class="lb">${l}</div><div class="tm">${t ? hhmm(t) : ""}</div></div>`;
  }).join("")}</div>`;
  const tsamples = (p.steps || []).filter((x) => x.kind === "tool" && x.output?.samples?.length).flatMap((x) => x.output.samples).slice(0, 4);
  const cands = p.candidates || [];
  const rec = cands[selCand] || p.action || {};
  const dr = rec.dry_run || p.dry_run;
  const checks = (dr?.checks || []).map((c) => `<div class="chk ${c.ok ? "y" : "n"}"><span class="m">${icon(c.ok ? "check" : "x", true)}</span><span>${esc(c.name)}<span class="d">${esc(c.detail)}</span></span></div>`).join("");
  const alts = cands.map((c, i) => { const ok = c.dry_run?.ok !== false;
    return `<label class="alt ${i === selCand ? "sel" : ""} ${ok ? "" : "blocked"}" onclick="pickCand(${i},${ok})"><input type="radio" name="cand" ${i === selCand ? "checked" : ""} ${ok ? "" : "disabled"}><span><b>${esc(c.label)}</b>${i === 0 ? ' <span class="small muted">· recommended</span>' : ""}<span class="small ${ok ? "ok" : "bad"}" style="display:block">${ok ? "Dry run passed" : "Dry run failed: " + esc((c.dry_run?.checks || []).filter((x) => !x.ok).map((x) => x.name).join(", "))}</span></span></label>`; }).join("");
  const fixCard = investigating
    ? `<div class="card"><h3>Recommended fix</h3><div class="wait"><span class="spin"></span><div><b>The AI is investigating</b><div class="small muted">${(p.steps || []).length} steps so far · usually 1-3 minutes</div></div></div></div>`
    : waiting ? `<div class="card"><h3>Recommended fix</h3>
      <div class="fixbox"><div class="small muted">${selCand === 0 ? "AI recommends" : "You picked"}</div><div class="a">${esc(rec.label)}</div></div>
      <div class="small mt" style="font-weight:600">Dry run ${dr?.ok ? '<span class="ok">passed</span>' : '<span class="bad">failed</span>'} <span class="muted" style="font-weight:400">- nothing has been changed yet</span></div>
      <div class="checks">${checks}</div>
      ${(dr?.changes || []).length ? `<details class="mini"><summary>What will change (${dr.changes.length})</summary><pre class="out">${esc(dr.changes.join("\n"))}</pre></details>` : ""}
      ${dr?.impact ? `<div class="small mt8"><span class="muted">Impact:</span> ${esc(dr.impact)}</div>` : ""}
      <div class="owner"><div><div style="font-weight:600">I'm the owner</div><div class="small muted">${esc(p.owner || "unassigned")} approves this fix</div></div>
        <label class="switch"><input type="checkbox" id="ownerok" ${ownerOk ? "checked" : ""} onchange="ownerOk=this.checked;syncApprove()" aria-label="I am the owner"><span></span></label></div>
      <label class="f" for="approver">Your name</label><input id="approver" value="${esc(store.get("approver"))}" placeholder="e.g. Napat" oninput="syncApprove()" autocomplete="name">
      <button class="btn lg mt" id="apbtn" data-dry="${dr?.ok ? 1 : 0}" onclick="approve(${p.id})">${rec.type === "manual" ? "Acknowledge - I'll handle it" : "Approve fix"}</button>
      <div style="display:flex;justify-content:space-between;align-items:center;margin-top:8px"><button class="btn danger" onclick="rejectInc(${p.id})">Reject</button><span class="small dim">Checked again right before it runs</span></div>
      ${cands.length > 1 ? `<details class="mini mt8"><summary>Other options (${cands.length - 1})</summary>${alts}</details>` : ""}
      <label class="f" for="apcomment">Comment (optional)</label><input id="apcomment" placeholder="Why approve or reject">
    </div>`
    : `<div class="card"><h3>Fix</h3><div class="fixbox"><div class="a">${esc((ex.action || p.action || {}).label || "No action")}</div></div>
      <div class="kv mt">${ex.approver ? `<div>Approved by</div><div>${esc(ex.approver)}${ex.owner ? " for " + esc(ex.owner) : ""}</div>` : ""}
      ${ex.preflight ? `<div>Re-checked</div><div class="${ex.preflight.ok ? "ok" : "bad"}">${ex.preflight.ok ? "Dry run passed again before applying" : "Failed"}</div>` : ""}
      ${ex.result ? `<div>Result</div><div class="${ex.result.ok ? "ok" : "bad"}">${esc(ex.result.detail)}</div>` : ""}
      ${ex.rejected ? "<div>Decision</div><div>Rejected</div>" : ""}
      ${ex.verification ? `<div>Verified</div><div class="${ex.verification.healthy ? "ok" : "bad"}">${ex.verification.healthy ? "Metrics back to normal" : "Still abnormal"}</div>` : ""}
      ${p.status === "verifying" ? '<div>Status</div><div class="muted">Checking the metrics...</div>' : ""}</div></div>`;
  $("#view").innerHTML = `<div class="page">${head(esc(p.title), `${p.entity_type === "host" ? "Computer" : "Service"} <b>${esc(p.entity)}</b>${(s.affected || []).length ? " · also affected " + s.affected.map(esc).join(", ") : ""} · detected ${hhmmss(p.detected_at)} · owner ${esc(p.owner || "-")}`,
      `${sevPill(p.severity)}${pill(p.status)}`, ["#/problems", "Problems"])}
    ${stepper}
    <div class="split mt"><div class="stack">
      <div class="card"><h3>What happened</h3>${p.root_cause ? `<div class="rc">${esc(p.root_cause)}</div><p class="muted" style="margin:10px 0 12px">${esc(p.summary)}</p>
        <div style="display:flex;align-items:center;gap:10px" class="small"><span class="muted">AI confidence</span><div class="conf"><div style="width:${(p.confidence || 0) * 100}%"></div></div><b>${Math.round((p.confidence || 0) * 100)}%</b></div>
        <div class="small dim mt8">${p.path === "known" ? "Matched a known problem from runbook memory" : `Written by ${esc(p.llm_model || "AI")}${p.llm_ok ? "" : " (from evidence)"}`} · analysis took ${dur((p.analysis_ms || 0) / 1000)}</div>`
        : `<div class="wait"><span class="spin"></span><div>The AI is reading metrics, traces and logs...</div></div>`}</div>
      ${(p.evidence || []).length ? `<div class="card"><h3>Evidence</h3>${p.evidence.map((e) => `<div class="ev"><span class="b"></span><span>${esc(e)}</span></div>`).join("")}
        ${tsamples.length ? `<div class="mt8 small" style="display:flex;gap:6px;flex-wrap:wrap;align-items:center"><span class="muted">Example traces</span>${tsamples.map((t) => `<button class="btn tint sm" onclick="showTrace('${esc(t.trace_id)}')">${esc(t.trace_id.slice(0, 8))}</button>`).join("")}</div>` : ""}</div>` : ""}
      ${(p.runbook || []).length ? `<div class="card"><h3>Runbook</h3><ol style="margin:0;padding-left:20px">${p.runbook.map((r) => `<li style="margin:4px 0">${esc(r)}</li>`).join("")}</ol></div>` : ""}
      <details class="disc"><summary><span>How the AI investigated <span class="muted" style="font-weight:400">· ${(p.steps || []).length} steps</span></span>${chev}</summary><div class="inner">${(p.steps || []).map(tlRow).join("") || '<div class="muted">Not started</div>'}</div></details>
    </div><div class="stack sticky">
      ${fixCard}
      <div class="card"><h3>Rate this analysis</h3><div class="stars" id="stars">${[1, 2, 3, 4, 5].map((n) => `<button aria-label="${n} stars" class="${n <= starScore ? "on" : ""}" onclick="setStars(${n})">&#9733;</button>`).join("")}</div>
        <div class="owner" style="margin-top:10px"><span>Root cause was correct</span><label class="switch"><input type="checkbox" id="rcaok" ${p.rca_correct === 0 ? "" : "checked"} aria-label="Root cause was correct"><span></span></label></div>
        <label class="f" for="fbtext">What should the AI learn?</label><textarea id="fbtext" rows="2">${esc(p.feedback || "")}</textarea>
        <button class="btn tint mt8" onclick="sendFeedback(${p.id})">Send feedback</button>
        <div class="small dim mt8">4-5 stars on a resolved problem saves it as a runbook. Low scores teach the AI for next time.</div></div>
      <div class="card"><h3>Notifications</h3>${(p.notifications || []).map((n) => `<div class="small" style="padding:3px 0">${esc(n.event.replace(/_/g, " "))} · ${hhmm(n.ts)} · <span class="muted">${esc(n.status)}</span></div>`).join("") || '<div class="small muted">None sent</div>'}
        ${p.status !== "analyzing" ? `<div class="mt8" style="display:flex;gap:6px;flex-wrap:wrap"><button class="btn plain sm" onclick="reanalyze(${p.id})">Run analysis again</button>${!["resolved", "closed", "rejected"].includes(p.status) ? `<button class="btn plain sm" onclick="closeInc(${p.id})">Close problem</button>` : ""}</div>` : ""}</div>
    </div></div></div>`;
  for (const [k, v] of Object.entries(keep)) if (v != null && $("#" + k)) $("#" + k).value = v;
  document.querySelectorAll("#view details").forEach((d, i) => { if (openD[i]) d.open = true; });
  syncApprove();
}
problemDetail.refresh = 4000;
const curId = () => location.hash.split("/").pop();
window.syncApprove = () => { const b = $("#apbtn"); if (b) b.disabled = b.dataset.dry === "0" || !(ownerOk && $("#approver")?.value.trim()); };
window.pickCand = (i, ok) => { if (!ok) return toast("This option failed its dry run"); selCand = i; problemDetail(curId(), false); };
window.setStars = (n) => { starScore = n; document.querySelectorAll("#stars button").forEach((e, i) => e.classList.toggle("on", i < n)); };
window.approve = async (id) => {
  const approver = $("#approver").value.trim(); store.set("approver", approver);
  const b = $("#apbtn"); b.disabled = true; b.textContent = "Re-checking dry run...";
  try { await api(`/api/incidents/${id}/approve`, {method: "POST", body: {approver, action_index: selCand, comment: $("#apcomment")?.value || "", owner_confirmed: ownerOk}}); toast("Approved. Applying the fix."); }
  catch (e) { toast(e.message); }
  lastKey = ""; problemDetail(id, false);
};
window.rejectInc = async (id) => { await api(`/api/incidents/${id}/reject`, {method: "POST", body: {approver: $("#approver")?.value.trim() || "owner", comment: $("#apcomment")?.value || ""}}); toast("Rejected"); lastKey = ""; problemDetail(id, false); };
window.closeInc = async (id) => { await api(`/api/incidents/${id}/close`, {method: "POST"}); lastKey = ""; problemDetail(id, false); };
window.reanalyze = async (id) => { await api(`/api/incidents/${id}/reanalyze`, {method: "POST"}); toast("Running the analysis again"); lastKey = ""; problemDetail(id, false); };
window.sendFeedback = async (id) => {
  if (!starScore) return toast("Tap a star first");
  const r = await api(`/api/incidents/${id}/feedback`, {method: "POST", body: {score: starScore, rca_correct: $("#rcaok").checked, comment: $("#fbtext").value}});
  toast(r.message === "feedback saved" ? "Thanks, feedback saved" : r.message); lastKey = "";
};

/* ======================= SERVICE MAP ======================= */
let mapSel = null, mapMode = "all";
async function serviceMap() {
  const d = await api("/api/servicemap");
  if (!changed({d, mapSel, mapMode})) return;
  const linked = new Set([...d.edges.flatMap((e) => [e.from, e.to]), ...d.entry]);
  const orphans = d.nodes.filter((n) => !linked.has(n.id));  // connected but no traffic yet: listed under the map
  const nodes = [{id: "clients", kind: "client", rps: null, instances: []}, ...d.nodes.filter((n) => linked.has(n.id))];
  const byId = Object.fromEntries(nodes.map((n) => [n.id, n]));
  const edges = [...d.edges.filter((e) => byId[e.from] && byId[e.to]), ...d.entry.filter((r) => byId[r]).map((r) => ({from: "clients", to: r, rps: byId[r].rps, error_rate: null}))];
  const layer = {clients: 0};
  for (let k = 0; k < 12; k++) for (const e of edges) if (layer[e.from] != null) layer[e.to] = Math.max(layer[e.to] ?? 0, layer[e.from] + 1);
  const maxL = Math.max(0, ...Object.values(layer));
  const cols = {};
  nodes.forEach((n) => { n.layer = layer[n.id] ?? maxL + 1; (cols[n.layer] = cols[n.layer] || []).push(n); });
  const W = 200, CW = 250, GAP = 22, TOP = 44;
  const nh = (n) => 68 + (n.instances.length ? 30 : 0);
  const colH = (ns) => ns.reduce((t, n) => t + nh(n) + GAP, -GAP);
  const H = Math.max(...Object.values(cols).map(colH)) + TOP + 70, Wd = 30 + (Math.max(...Object.keys(cols).map(Number)) + 1) * CW;
  Object.entries(cols).forEach(([l, ns]) => { let y = TOP + (H - TOP - 70 - colH(ns)) / 2; ns.sort((a, b) => a.id.localeCompare(b.id)).forEach((n) => { n.x = 24 + Number(l) * CW; n.y = y; y += nh(n) + GAP; }); });
  const thr = 0.05, bad = (n) => !!n.problem_id || (n.error_rate ?? 0) > thr || n.instances.some((i) => i.problem_id || i.error_rate > thr);
  let keepSet = null;  // "Problems only": the path from clients down to each failing box
  if (mapMode === "problems") {
    keepSet = new Set();
    const up = (id) => { if (keepSet.has(id)) return; keepSet.add(id); edges.filter((e) => e.to === id).forEach((e) => up(e.from)); };
    nodes.filter(bad).forEach((n) => up(n.id));
  }
  const hl = mapSel ? new Set(edges.filter((e) => e.from === mapSel || e.to === mapSel).map((e) => e.from + ">" + e.to)) : null;
  const svgEdges = edges.map((e) => {
    const a = byId[e.from], b = byId[e.to];
    const x1 = a.x + W, y1 = a.y + nh(a) / 2, x2 = b.x - 4, y2 = b.y + nh(b) / 2, mx = (x1 + x2) / 2;
    const isBad = (e.error_rate ?? 0) > thr, on = hl?.has(e.from + ">" + e.to), faded = (keepSet && !(keepSet.has(e.from) && keepSet.has(e.to))) || (hl && !on);
    return `<path d="M${x1} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2} ${y2}" class="edge ${isBad ? "bad" : ""} ${on ? "hl" : ""} ${faded ? "faded" : ""}" marker-end="url(#ah${isBad ? "b" : on ? "h" : ""})"><title>${esc(e.from)} to ${esc(e.to)}: ${num(e.rps, 2)} req/s${e.error_rate != null ? ", " + pct(e.error_rate) + " errors" : ""}</title></path>
      ${(on || isBad) && !faded ? `<text x="${mx}" y="${(y1 + y2) / 2 - 7}" text-anchor="middle" class="elbl ${isBad ? "bad" : ""}">${num(e.rps, 1)}/s${isBad ? " · " + pct(e.error_rate, 0) : ""}</text>` : ""}`;
  }).join("");
  const kindTxt = (n) => n.kind === "client" ? "Users on the internet" : n.kind === "network" ? (n.id.includes("firewall") ? "Firewall" : "Load balancer") : `Service · ${n.owner || "no owner"}`;
  const svgNodes = nodes.map((n) => {
    const b = bad(n), faded = keepSet && !keepSet.has(n.id);
    const metric = n.kind === "client" ? "" : n.rps == null ? "no traffic yet" : `${num(n.rps, 1)} req/s · ${pct(n.error_rate, 1)} errors`;
    const tot = n.instances.reduce((t, i) => t + (i.rps || 0), 0) || 1;
    const chips = n.instances.map((i, k) => { const w = (W - 24 - (n.instances.length - 1) * 6) / n.instances.length, ib = i.problem_id || i.error_rate > thr;
      return `<g class="ichip ${ib ? "bad" : ""}" transform="translate(${n.x + 12 + k * (w + 6)},${n.y + 64})"><rect width="${w}" height="24" rx="7"/><text x="8" y="16">${esc(i.id.replace(n.id + "-", ""))} · ${Math.round(((i.rps || 0) / tot) * 100)}%${ib ? " · " + pct(i.error_rate, 0) : ""}</text></g>`; }).join("");
    const logo = n.kind === "client" ? fiUrl("globe") : `/static/icons/b/${langOf(n.kind === "network" ? "nginx" : n.language) || "docker"}.svg`;
    const [fg, bg] = n.kind === "client" ? ["var(--blue)", "var(--blue-tint)"] : b ? ["var(--bad)", "var(--bad-bg)"] : n.rps == null ? ["var(--text-3)", "var(--fill)"] : ["var(--ok)", "var(--ok-bg)"];
    return `<g class="node ${b ? "bad" : ""} ${mapSel === n.id ? "sel" : ""} ${faded ? "faded" : ""}" onclick="mapPick('${esc(n.id)}')" role="button" aria-label="${esc(n.id)}">
      <rect class="box" x="${n.x}" y="${n.y}" width="${W}" height="${nh(n)}" rx="14"/>
      <circle cx="${n.x + 24}" cy="${n.y + 24}" r="14" style="fill:${n.kind === "client" ? bg : "var(--fill)"}"/>
      <image href="${logo}" x="${n.x + 15}" y="${n.y + 15}" width="18" height="18"/>
      <circle cx="${n.x + 34}" cy="${n.y + 14}" r="4.5" style="fill:${n.kind === "client" ? "transparent" : b ? "var(--bad-dot)" : n.rps == null ? "var(--gray-dot)" : "var(--ok-dot)"}"/>
      <text x="${n.x + 46}" y="${n.y + 22}" class="nm">${esc(n.id === "clients" ? "Clients" : n.id)}</text>
      <text x="${n.x + 46}" y="${n.y + 38}" class="kd">${esc(kindTxt(n))}</text>
      <text x="${n.x + 14}" y="${n.y + 57}" class="kp ${b ? "bad" : ""}">${metric}${n.problem_id ? " · P-" + n.problem_id : ""}</text>${chips}</g>`;
  }).join("");
  const lanes = ["CLIENTS", "PERIMETER", "LOAD BALANCING", "WEB", "APPLICATION", "BACKEND", "DATA"];
  const sel = mapSel && byId[mapSel];
  $("#view").innerHTML = `<div class="page" style="max-width:1400px">${head("Service Map", "Every hop a request takes, left to right. Tap a box to see its details.",
      `<div class="seg" role="group" aria-label="Filter"><button class="${mapMode === "all" ? "on" : ""}" onclick="mapMode='all';serviceMap()">All</button><button class="${mapMode === "problems" ? "on" : ""}" onclick="mapMode='problems';serviceMap()">Problems only</button></div>`)}
    <div class="mapwrap ${sel ? "has-side" : ""}"><div class="mapcard"><svg class="smap" viewBox="0 0 ${Wd} ${H}" style="width:100%;min-width:${Math.min(Wd, 860)}px;height:auto" preserveAspectRatio="xMinYMin meet">
      <defs>${[["ah", "#c7c7cc"], ["ahb", "#ff3b30"], ["ahh", "#0078d4"]].map(([i, c]) => `<marker id="${i}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 1 9 5 0 9z" fill="${c}"/></marker>`).join("")}</defs>
      ${Object.keys(cols).map((l) => `<text x="${24 + l * CW}" y="22" class="lane">${lanes[l] || "TIER " + l}</text>`).join("")}
      ${svgEdges}${svgNodes}
      <rect x="16" y="${H - 52}" width="${Wd - 32}" height="38" rx="10" class="host"/>
      <text x="32" y="${H - 28}" class="kd">Runs on ${d.hosts.map((h) => esc(h.name)).join(", ")} · based on ${d.traces_sampled} recent traces</text>
    </svg></div>${sel ? sidePanel(sel, edges) : ""}</div>
    <div class="small dim mt8">Red means more than 5% of requests failed. The percentages inside a box show how the load balancer splits traffic.</div>
    ${orphans.length ? `<div class="small muted mt8">Not on the map yet (no traffic): ${orphans.map((n) => `<a href="#/services/${esc(n.id)}">${esc(n.id)}</a>`).join(", ")}</div>` : ""}</div>`;
}
serviceMap.refresh = 15000;
function sidePanel(n, edges) {
  const inn = edges.filter((e) => e.to === n.id), out = edges.filter((e) => e.from === n.id);
  const row = (e, other) => `<div class="li noicon tap" onclick="mapPick('${esc(other)}')"><div class="tx"><div class="t">${esc(other === "clients" ? "Clients" : other)}</div></div><span class="acc">${num(e.rps, 1)}/s${e.error_rate > 0.05 ? ` · <span class="bad">${pct(e.error_rate, 0)}</span>` : ""}</span>${chev}</div>`;
  return `<div class="side-panel stack"><div class="card"><div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px"><div><h2>${esc(n.id === "clients" ? "Clients" : n.id)}</h2><div class="small muted">${n.kind === "client" ? "Users on the internet" : n.kind === "network" ? "Network device" : "Service"}${n.owner ? " · " + esc(n.owner) : ""}</div></div>
      <button class="btn plain sm" onclick="mapPick(null)">Done</button></div>
    ${n.kind !== "client" ? `<div class="grid g3 mt"><div><div class="small muted">Requests</div><b>${num(n.rps, 1)}/s</b></div><div><div class="small muted">Errors</div><b class="${n.error_rate > 0.05 ? "bad" : ""}">${pct(n.error_rate)}</b></div><div><div class="small muted">p95</div><b>${ms(n.p95_ms)}</b></div></div>` : ""}
    ${n.instances.length ? `<div class="small muted mt">Instances</div>${n.instances.map((i) => `<div class="meter" style="grid-template-columns:90px minmax(0,1fr) 60px"><span>${esc(i.id)}</span><div class="bar"><div style="width:${((i.rps || 0) / (n.rps || 1)) * 100}%;background:${i.error_rate > 0.05 ? "var(--bad-dot)" : "var(--blue)"}"></div></div><span class="p">${pct(i.error_rate)}</span></div>`).join("")}` : ""}
    <div class="mt" style="display:flex;gap:8px;flex-wrap:wrap">${n.problem_id ? `<a class="btn" href="#/problems/${n.problem_id}">Open problem P-${n.problem_id}</a>` : ""}${n.kind !== "client" ? `<a class="btn tint" href="#/services/${esc(n.id)}">Service details</a>` : ""}</div></div>
    ${inn.length ? `<div class="sec-h" style="margin-left:4px">Called by</div><div class="list">${inn.map((e) => row(e, e.from)).join("")}</div>` : ""}
    ${out.length ? `<div class="sec-h" style="margin-left:4px">Calls</div><div class="list">${out.map((e) => row(e, e.to)).join("")}</div>` : ""}</div>`;
}
window.mapPick = (id) => { mapSel = id; serviceMap(); };

/* ======================= SERVICES ======================= */
async function services() {
  if (typing()) return;
  const [apps, disc] = await Promise.all([api("/api/apps"), api("/api/discover").catch(() => ({services: []}))]);
  if (!changed({apps, disc})) return;
  const svc = apps.filter((a) => a.kind !== "network"), net = apps.filter((a) => a.kind === "network");
  $("#view").innerHTML = `<div class="page">${head("Services", "Applications that send traces and logs to AIOps.", '<a class="btn" href="#/connect/service">Connect a service</a>')}
    ${disc.services.length ? `<div class="sec-h">Found, not added yet</div><div class="list">${disc.services.map((s) => `<div class="li">${ibox("sparkle", "var(--blue)")}<div class="tx"><div class="t">${esc(s.service_name)}</div><div class="s">Already sending data${s.rps ? ` · ${num(s.rps, 2)} req/s` : ""}</div></div><button class="btn sm" onclick="quickAdd('${esc(s.service_name)}')">Add</button></div>`).join("")}</div>` : ""}
    <div class="sec-h">Applications (${svc.length})</div><div class="list">${svc.map(svcRow).join("") || '<div class="empty">None yet</div>'}</div>
    ${net.length ? `<div class="sec-h">Network devices</div><div class="list">${net.map(svcRow).join("")}</div>` : ""}</div>`;
}
services.refresh = 10000;
window.quickAdd = (svc) => openModal(`<h2>Add ${esc(svc)}</h2><p class="sub">Who owns this service? The owner approves fixes for it.</p>
  <label class="f" for="qa_owner">Owner team</label><input id="qa_owner" placeholder="team-orders" value="${esc(store.get("lastOwner"))}">
  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:18px"><button class="btn plain" onclick="closeModal()">Cancel</button><button class="btn" onclick="doQuickAdd('${esc(svc)}')">Add service</button></div>`, 460);
window.doQuickAdd = async (svc) => {
  const owner = $("#qa_owner").value.trim() || "unassigned"; store.set("lastOwner", owner);
  try { await api("/api/apps", {method: "POST", body: {service_name: svc, owner}}); toast(`${svc} added`); closeModal(); lastKey = ""; services(); } catch (e) { toast(e.message); }
};

async function serviceDetail(svc) {
  const d = await api(`/api/services/${svc}`);
  if (!changed(d)) return;
  const h = d.health, a = d.app;
  $("#view").innerHTML = `<div class="page">${head(esc(a.name), `${esc(a.service_name)} · owner ${esc(a.owner || a.team || "-")}${h.version ? ` · v${esc(h.version)} (${esc(h.commit)})` : ""}`,
      h.problem_id ? `<a class="btn" href="#/problems/${h.problem_id}">Open problem P-${h.problem_id}</a>` : `<span class="pill ${h.status === "healthy" ? "p-ok" : ""}">${h.status === "healthy" ? "Healthy" : "No data yet"}</span>`, ["#/services", "Services"])}
    <div class="grid g3">${chartCard(d.series.rps, {title: "Requests / s"})}${chartCard(d.series.error_rate, {title: "Error rate", color: "var(--c-red)", fmt: (v) => pct(v)})}${chartCard(d.series.p95, {title: "Response time (p95)", color: "var(--c-orange)", fmt: ms})}</div>
    <div class="grid g2 mt">
      <div><div class="sec-h">Endpoints</div><div class="list plain">${d.endpoints.map((e) => `<div class="li noicon"><div class="tx"><div class="t mono">${esc(e.name)}</div></div><span class="acc">${e.rps}/s · <span class="${e.error_rate > 0.05 ? "bad" : ""}">${pct(e.error_rate)}</span></span></div>`).join("") || '<div class="empty">No requests yet</div>'}</div>
        <div class="sec-h">Errors by version</div><div class="list plain">${d.versions.map((v) => `<div class="li noicon"><div class="tx"><div class="t">v${esc(v.version)} <span class="mono muted">${esc(v.commit)}</span></div></div><span class="acc ${v.error_rate > 0.05 ? "bad" : ""}">${pct(v.error_rate)}</span></div>`).join("") || '<div class="empty">No version data</div>'}</div></div>
      <div><div class="sec-h">Recent traces</div><div class="list plain">${d.traces.slice(0, 8).map((t) => `<div class="li noicon tap" onclick="showTrace('${esc(t.traceID)}')"><div class="tx"><div class="t">${esc(t.rootTraceName)}</div><div class="s">${esc(t.rootServiceName)} · ${hhmmss(t.startTimeUnixNano / 1e9)}</div></div><span class="acc">${t.durationMs ?? 0} ms</span>${chev}</div>`).join("") || '<div class="empty">No traces yet</div>'}</div>
        <div class="sec-h">Deployments</div><div class="list plain">${d.deployments.slice(0, 6).map((x) => `<div class="li noicon"><div class="tx"><div class="t">v${esc(x.version)} <span class="mono muted">${esc(x.commit_hash)}</span></div><div class="s">${esc(x.author)} · ${esc(x.message)}</div></div><span class="acc">${ago(x.ts)}</span></div>`).join("") || '<div class="empty">No deployments recorded</div>'}</div></div>
    </div>
    <div class="sec-h">Logs</div><div class="card">${d.logs.length ? d.logs.map((l) => `<div class="logline"><span class="dim">${hhmmss(l.ts)}</span><span class="lv lv-${esc(l.level)}">${esc(l.level)}</span><span>${esc(l.line)}</span></div>`).join("") : '<div class="empty">No logs in the last 15 minutes</div>'}</div>
    <div class="mt"><button class="btn danger sm" onclick="removeApp(${a.id},'${esc(a.service_name)}')">Remove this service</button></div></div>`;
}
serviceDetail.refresh = 15000;
window.removeApp = (id, name) => openModal(`<h2>Remove ${esc(name)}?</h2><p class="sub">AIOps stops raising problems for it. Its data stays until it expires.</p>
  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:18px"><button class="btn plain" onclick="closeModal()">Cancel</button><button class="btn" style="background:var(--bad)" onclick="doRemoveApp(${id})">Remove</button></div>`, 460);
window.doRemoveApp = async (id) => { await api(`/api/apps/${id}`, {method: "DELETE"}); closeModal(); location.hash = "#/services"; };

async function showTrace(id) {
  const spans = await api(`/api/traces/${id}`);
  if (!spans.length) return toast("Trace not available yet");
  const t0 = Math.min(...spans.map((s) => s.start)), t1 = Math.max(...spans.map((s) => s.end)), span = t1 - t0 || 1;
  const byId = Object.fromEntries(spans.map((s) => [s.id, s])), depth = {};
  const dep = (s) => depth[s.id] ?? (depth[s.id] = byId[s.parent] ? dep(byId[s.parent]) + 1 : 0);
  openModal(`<h2>Request trace</h2><p class="sub mono">${esc(id)} · ${spans.length} steps · ${ms(span)}</p><div class="mt">
    ${spans.map((s) => `<div class="wf-row"><div style="padding-left:${dep(s) * 12}px;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" class="${s.error ? "bad" : ""}"><b>${esc(s.instance || s.service)}</b> <span class="muted">${esc(s.name)}</span></div>
      <div class="wf"><div class="b ${s.error ? "err" : ""}" style="left:${((s.start - t0) / span) * 100}%;width:${Math.max(((s.end - s.start) / span) * 100, 0.5)}%"></div></div><div class="small muted" style="text-align:right">${ms(s.end - s.start)}</div></div>
      ${s.error && s.status_msg ? `<div class="small bad" style="padding:2px 0 4px ${dep(s) * 12 + 4}px">${esc(s.status_msg)}</div>` : ""}`).join("")}</div>`);
}
window.showTrace = showTrace;

/* ======================= COMPUTERS ======================= */
async function infra() {
  const hosts = await api("/api/hosts");
  if (!changed(hosts)) return;
  $("#view").innerHTML = `<div class="page">${head("Computers & Servers", "Machines that report CPU, memory and disk to AIOps.", '<a class="btn" href="#/connect/computer">Connect a computer</a>')}
    <div class="grid g3">${hosts.map((h) => `<a class="card" href="#/infra/${esc(h.name)}" style="color:inherit;display:block">
      <div style="display:flex;gap:12px;align-items:center"><span class="li" style="padding:0;min-height:0">${hostBox(h)}</span>
        <div style="flex:1;min-width:0"><div style="font-weight:600">${esc(h.name)}</div><div class="small muted" style="white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(h.os || "")}</div></div>
        ${h.problem_id ? problemPill : h.status === "healthy" ? '<span class="pill p-ok">Online</span>' : `<span class="pill">${h.status === "offline" ? "Offline" : "Waiting"}</span>`}</div>
      <div class="mt8">${meter("CPU", h.cpu)}${meter("Memory", h.mem, 80, 90)}${meter("Disk", h.disk, 80, 90)}</div>
      <div class="small dim mt8">${h.agent === "aiops-agent" ? "AIOps agent · sends data itself" : "node_exporter · AIOps collects"}</div></a>`).join("")}
      <a class="card" href="#/connect/computer" style="display:grid;place-items:center;color:var(--blue);min-height:180px;border:2px dashed var(--blue-tint-2);box-shadow:none;background:transparent"><div style="text-align:center">${icon("plus", false, 30)}<div style="font-weight:600;margin-top:6px">Connect a computer</div></div></a></div></div>`;
}
infra.refresh = 10000;
async function hostDetail(name) {
  const d = await api(`/api/hosts/${name}`);
  if (!changed(d)) return;
  const h = d.host;
  $("#view").innerHTML = `<div class="page">${head(esc(h.name), `${esc(h.os || "")} · ${h.agent === "aiops-agent" ? "AIOps agent" : esc(h.address)} · owner ${esc(h.owner || "-")}`,
      h.problem_id ? `<a class="btn" href="#/problems/${h.problem_id}">Open problem P-${h.problem_id}</a>` : `<span class="pill ${h.status === "healthy" ? "p-ok" : ""}">${h.status === "healthy" ? "Online" : h.status === "offline" ? "Offline" : "Waiting"}</span>`, ["#/infra", "Computers"])}
    <div class="grid g4">${chartCard(d.series.cpu, {title: "CPU", fmt: (v) => Math.round(v) + "%"})}${chartCard(d.series.mem, {title: "Memory", color: "var(--c-purple)", fmt: (v) => Math.round(v) + "%"})}
      ${chartCard(d.series.disk, {title: "Disk", color: "var(--c-teal)", fmt: (v) => Math.round(v) + "%"})}${chartCard(d.series.load, {title: "Load (1 min)", color: "var(--c-orange)"})}</div>
    ${d.processes.length ? `<div class="sec-h">Busiest processes</div><div class="list plain">${d.processes.map((p) => `<div class="li noicon"><div class="tx"><div class="t">${esc(p.name)}</div><div class="s">PID ${p.pid}</div></div><span class="acc">CPU ${num(p.cpu, 1)}% · Memory ${num(p.mem, 1)}%</span></div>`).join("")}</div>` : ""}
    ${d.containers.length ? `<div class="sec-h">Containers</div><div class="list plain">${d.containers.map((c) => `<div class="li noicon"><div class="tx"><div class="t">${esc(c.name)}</div><div class="s mono">${esc(c.image)}</div></div><span class="acc ${c.cpu_pct > 50 ? "bad" : ""}">CPU ${num(c.cpu_pct)}% · ${num(c.mem_mb, 0)} MB</span></div>`).join("")}</div>` : ""}
    <div class="mt"><button class="btn danger sm" onclick="removeHost(${h.id},'${esc(h.name)}')">Remove this computer</button></div></div>`;
}
hostDetail.refresh = 15000;
window.removeHost = (id, name) => openModal(`<h2>Remove ${esc(name)}?</h2><p class="sub">AIOps stops watching it. To also stop the agent on that machine, run this there:</p>
  <div class="code mt">curl -fsSL ${esc(location.origin)}/install/uninstall.sh | sh</div>
  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:18px"><button class="btn plain" onclick="closeModal()">Cancel</button><button class="btn" style="background:var(--bad)" onclick="doRemoveHost(${id})">Remove</button></div>`, 520);
window.doRemoveHost = async (id) => { await api(`/api/hosts/${id}`, {method: "DELETE"}); closeModal(); location.hash = "#/infra"; };

/* ======================= CONNECT ======================= */
const codeBox = (txt, id) => `<div class="code" id="${id}"><span>${esc(txt)}</span><button class="cp" onclick="copyCode('${id}')">Copy</button></div>`;
window.copyCode = (id) => {
  const el = document.querySelector(`#${id} span`), txt = el.textContent;
  const fallback = () => { const r = document.createRange(); r.selectNodeContents(el); getSelection().removeAllRanges(); getSelection().addRange(r); toast("Selected. Press Cmd+C to copy"); };
  try { navigator.clipboard.writeText(txt).then(() => toast("Copied"), fallback); } catch { fallback(); }
};
const waitBox = (t) => `<div class="wait"><span class="spin"></span><div>${esc(t)}<div class="small muted">This updates by itself.</div></div></div>`;
const okBox = (t, sub) => `<div class="wait ok">${icon("check", false, 22)}<div><b>${esc(t)}</b><div class="small">${sub}</div></div></div>`;
function connectHub() {
  $("#view").innerHTML = `<div class="page">${head("Connect", "What do you want AIOps to watch?")}
    <div class="choice">
      <a href="#/connect/service"><span class="ic" style="background:var(--blue)">${icon("cube")}</span><b>A service</b><span class="muted">Your web app or API. Add a few settings and its traces and logs start flowing.</span><span class="logos">${["python", "node", "java", "dotnet", "docker"].map((k) => brand(k, 26, k)).join("")}${brand("otel", 26, "OpenTelemetry")}</span><span style="color:var(--blue);font-weight:600">3 steps ›</span></a>
      <a href="#/connect/computer"><span class="ic" style="background:var(--c-purple)">${icon("laptop")}</span><b>A computer or server</b><span class="muted">A Mac, a Linux server or a VM. Paste one command in Terminal and it reports CPU, memory, disk and its busiest processes.</span><span class="logos">${brand("apple", 26, "macOS")}${brand("linux", 26, "Linux")}</span><span style="color:var(--blue);font-weight:600">1 command ›</span></a>
    </div>
    <div class="sec-h">Good to know</div>
    <div class="list plain"><div class="li noicon"><div class="tx"><div class="t">Outbound only</div><div class="s">Your machines send data to AIOps. Nothing needs to be opened on them.</div></div></div>
      <div class="li noicon"><div class="tx"><div class="t">Network</div><div class="s">They must reach ${esc(location.hostname)} on ports 8080 and 4318 (KMUTT network or VPN).</div></div></div>
      <div class="li noicon"><div class="tx"><div class="t">Safety</div><div class="s">AIOps never runs anything on a connected computer. Automatic fixes are only for services you add here, and always need the owner's approval.</div></div></div></div></div>`;
}

let cc = {name: "", os: "mac", waitFor: null};
const ccCmd = () => `curl -fsSL ${location.origin}/install/agent.sh | AIOPS_HOST_NAME=${cc.name} sh`;
function connectComputer() {
  cc.name = cc.name || store.get("ccName", "my-mac");
  $("#view").innerHTML = `<div class="page" style="max-width:760px">${head("Connect a computer", "", "", ["#/connect", "Connect"])}
    <div class="steps">
      <div class="step-card done"><span class="n">1</span><h2>Name it</h2><div class="bd">
        <label class="f" for="cc_name">Computer name</label><input id="cc_name" value="${esc(cc.name)}" oninput="ccRename(this.value)" autocomplete="off" spellcheck="false">
        <label class="f">System</label><div class="seg" role="group"><button class="${cc.os === "mac" ? "on" : ""}" onclick="cc.os='mac';connectComputer()">${brand("apple", 16)}macOS</button><button class="${cc.os === "linux" ? "on" : ""}" onclick="cc.os='linux';connectComputer()">${brand("linux", 16)}Linux</button></div></div></div>
      <div class="step-card done"><span class="n">2</span><h2>Paste this in Terminal ${cc.os === "mac" ? "on the Mac" : "on the server"}</h2><div class="bd">
        <div id="cc_cmd_wrap">${codeBox(ccCmd(), "cc_cmd")}</div>
        <div class="small muted mt8">${cc.os === "mac" ? "No admin password, nothing opened on your Mac. It starts again by itself when you log in." : "No sudo needed, only python3. It starts again after a reboot."}</div></div></div>
      <div class="step-card"><span class="n">3</span><h2>Wait for it to appear</h2><div class="bd" id="cc_wait">${waitBox("Waiting for " + cc.name + "...")}</div></div>
    </div>
    <details class="disc mt"><summary><span>Advanced: server that already runs node_exporter</span>${chev}</summary><div class="inner">
      <p class="small muted">AIOps will collect from it on port 9100, so it must be reachable from ${esc(location.hostname)}.</p>
      <label class="f" for="ne_name">Name</label><input id="ne_name" placeholder="db-01">
      <label class="f" for="ne_addr">Address</label><input id="ne_addr" placeholder="10.4.82.30:9100">
      <button class="btn tint mt" onclick="addNodeExporter()">Add server</button></div></details></div>`;
  cc.waitFor = cc.name; pollComputer();
}
window.ccRename = (v) => {
  cc.name = v.toLowerCase().replace(/\s+/g, "-").replace(/[^a-z0-9._-]/g, "") || "my-mac"; store.set("ccName", cc.name); cc.waitFor = cc.name;
  $("#cc_cmd_wrap").innerHTML = codeBox(ccCmd(), "cc_cmd");
  $("#cc_wait").innerHTML = waitBox("Waiting for " + cc.name + "...");
};
async function pollComputer() {
  const el = $("#cc_wait"); if (!el || !cc.waitFor) return;
  const hosts = await api("/api/hosts").catch(() => []);
  const h = hosts.find((x) => x.name === cc.waitFor);
  if (!h) return;
  if (h.status === "healthy" || h.status === "problem") {
    el.closest(".step-card").classList.add("done");
    el.innerHTML = okBox(`${h.name} is connected`, hostLine(h)) + `<a class="btn mt" href="#/infra/${esc(h.name)}">View ${esc(h.name)}</a>`;
    cc.waitFor = null;
  } else el.innerHTML = waitBox(`${h.name} is registered. Waiting for its first measurements...`);
}
setInterval(() => { if ((location.hash || "").startsWith("#/connect/computer") && !document.hidden) pollComputer(); }, 3000);
window.addNodeExporter = async () => {
  const body = {name: $("#ne_name").value.trim(), address: $("#ne_addr").value.trim()};
  if (!body.name || !body.address) return toast("Enter a name and an address");
  try { await api("/api/hosts", {method: "POST", body}); toast("Server added. First data within 15 s."); location.hash = "#/infra/" + body.name; } catch (e) { toast(e.message); }
};

let cs = {step: 1, svc: "", owner: "", rt: "python"}, otlpPublic = "";
const SNIP = {
  python: (s, o) => `pip install opentelemetry-distro opentelemetry-exporter-otlp
opentelemetry-bootstrap -a install

export OTEL_SERVICE_NAME=${s}
export OTEL_EXPORTER_OTLP_ENDPOINT=${o}
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export OTEL_LOGS_EXPORTER=otlp
export OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true

opentelemetry-instrument python app.py`,
  node: (s, o) => `npm install @opentelemetry/api @opentelemetry/auto-instrumentations-node

export OTEL_SERVICE_NAME=${s}
export OTEL_EXPORTER_OTLP_ENDPOINT=${o}
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf
export NODE_OPTIONS="--require @opentelemetry/auto-instrumentations-node/register"

node app.js`,
  java: (s, o) => `curl -LO https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar

export OTEL_SERVICE_NAME=${s}
export OTEL_EXPORTER_OTLP_ENDPOINT=${o}
export OTEL_EXPORTER_OTLP_PROTOCOL=http/protobuf

java -javaagent:./opentelemetry-javaagent.jar -jar app.jar`,
  dotnet: (s, o) => `curl -sSfL https://github.com/open-telemetry/opentelemetry-dotnet-instrumentation/releases/latest/download/otel-dotnet-auto-install.sh -O
sh ./otel-dotnet-auto-install.sh
. $HOME/.otel-dotnet-auto/instrument.sh

export OTEL_SERVICE_NAME=${s}
export OTEL_EXPORTER_OTLP_ENDPOINT=${o}

dotnet run`,
  docker: (s, o) => `# docker-compose.yml: add under your service
    environment:
      OTEL_SERVICE_NAME: ${s}
      OTEL_EXPORTER_OTLP_ENDPOINT: ${o}
      OTEL_EXPORTER_OTLP_PROTOCOL: http/protobuf
      OTEL_LOGS_EXPORTER: otlp`,
  test: (s, o) => {
    const hex = (n) => [...crypto.getRandomValues(new Uint8Array(n))].map((b) => b.toString(16).padStart(2, "0")).join("");
    const t = BigInt(Date.now()) * 1000000n;
    const body = {resourceSpans: [{resource: {attributes: [{key: "service.name", value: {stringValue: s}}]}, scopeSpans: [{spans: [{traceId: hex(16), spanId: hex(8), name: "GET /hello", kind: 2,
      startTimeUnixNano: String(t), endTimeUnixNano: String(t + 42000000n), status: {}}]}]}]};
    return `# sends one test request trace. No app needed.\ncurl -X POST ${o}/v1/traces -H 'Content-Type: application/json' \\\n  -d '${JSON.stringify(body)}'`;
  },
};
const RT = [["python", "Python"], ["node", "Node.js"], ["java", "Java"], ["dotnet", ".NET"], ["docker", "Docker"], ["test", "Just test", "otel"]];
async function connectService() {
  if (!otlpPublic) otlpPublic = (await api("/api/discover").catch(() => ({}))).otlp_endpoint || location.origin.replace(/:\d+$/, ":4318");
  const s = cs.svc || "my-service";
  const st = (n) => cs.step > n ? "done" : cs.step === n ? "" : "todo";
  $("#view").innerHTML = `<div class="page" style="max-width:760px">${head("Connect a service", "", "", ["#/connect", "Connect"])}
    <div class="steps">
      <div class="step-card ${st(1)}"><span class="n">1</span><h2>Name your service</h2><div class="bd">
        ${cs.step === 1 ? `<label class="f" for="cs_svc">Service name</label><input id="cs_svc" value="${esc(cs.svc)}" placeholder="order-api" autocomplete="off" spellcheck="false">
          <label class="f" for="cs_owner">Owner team <span class="dim">(approves fixes)</span></label><input id="cs_owner" value="${esc(cs.owner || store.get("lastOwner"))}" placeholder="team-orders">
          <button class="btn mt" onclick="csNext()">Continue</button>` : `<div><b>${esc(cs.svc)}</b> <span class="muted">· owner ${esc(cs.owner)}</span> <button class="btn plain sm" onclick="cs.step=1;connectService()">Change</button></div>`}</div></div>
      <div class="step-card ${cs.step >= 2 ? "done" : "todo"}"><span class="n">2</span><h2>Turn on OpenTelemetry</h2><div class="bd">
        ${cs.step >= 2 ? `<div class="seg" role="group" style="margin-bottom:12px">${RT.map(([k, l, logo]) => `<button class="${cs.rt === k ? "on" : ""}" onclick="cs.rt='${k}';connectService()">${brand(logo || k, 16)}${l}</button>`).join("")}</div>
          ${codeBox(SNIP[cs.rt](s, otlpPublic), "cs_snip")}
          <div class="small muted mt8">${cs.rt === "test" ? "Run this to check the connection before touching your app." : "No code changes. Restart your app with these settings."}</div>
          <details class="mini mt8"><summary>Optional: link deployments to problems</summary><p class="small muted">Add this to the end of your CI pipeline so the AI can tie a problem to the commit behind it.</p>
          ${codeBox(`curl -X POST ${location.origin}/api/deployments -H 'Content-Type: application/json' \\\n  -d '{"service":"${s}","version":"1.4.0","commit":"'$CI_COMMIT_SHORT_SHA'","author":"'$GITLAB_USER_LOGIN'"}'`, "cs_ci")}</details>` : '<div class="muted small">Pick your language after step 1.</div>'}</div></div>
      <div class="step-card ${cs.step === 3 ? "done" : cs.step === 2 ? "" : "todo"}"><span class="n">3</span><h2>Check the data arrives</h2><div class="bd" id="cs_wait">${cs.step >= 2 ? waitBox(`Waiting for the first data from ${s}...`) : '<div class="muted small">Starts after step 2.</div>'}</div></div>
    </div></div>`;
  if (cs.step >= 2) pollService();
}
window.csNext = async () => {
  const svc = $("#cs_svc").value.trim().toLowerCase().replace(/\s+/g, "-"), owner = $("#cs_owner").value.trim() || "unassigned";
  if (!svc) return toast("Enter a service name");
  cs.svc = svc; cs.owner = owner; store.set("lastOwner", owner);
  try { await api("/api/apps", {method: "POST", body: {service_name: svc, owner}}); } catch (e) { if (!/already/.test(e.message)) return toast(e.message); }
  cs.step = 2; connectService();
};
async function pollService() {
  const el = $("#cs_wait"); if (!el || cs.step < 2) return;
  const v = await api(`/api/apps/${encodeURIComponent(cs.svc)}/verify`).catch(() => null);
  if (!v || !(v.metrics || v.traces || v.logs)) return;
  const tick = (b, l) => `<span class="pill ${b ? "p-ok" : ""}">${b ? "✓ " : ""}${l}</span>`;
  cs.step = 3; el.closest(".step-card").classList.remove("todo"); el.closest(".step-card").classList.add("done");
  el.innerHTML = okBox(`${cs.svc} is sending data`, `<span style="display:flex;gap:6px;flex-wrap:wrap;margin-top:4px">${tick(v.traces, "traces")}${tick(v.metrics, "metrics")}${tick(v.logs, "logs")}</span>`) +
    `<div class="mt" style="display:flex;gap:8px;flex-wrap:wrap"><a class="btn" href="#/services/${esc(cs.svc)}">Open ${esc(cs.svc)}</a><a class="btn tint" href="#/map">See it on the map</a><button class="btn plain" onclick="cs={step:1,svc:'',owner:'',rt:'python'};connectService()">Connect another</button></div>`;
}
setInterval(() => { if ((location.hash || "").startsWith("#/connect/service") && !document.hidden && cs.step === 2) pollService(); }, 4000);

/* ======================= AI pages ======================= */
async function skillsView() {
  const sk = await api("/api/skills");
  $("#view").innerHTML = `<div class="page">${head("Skills & Scores", "The AI picks one skill per problem. Skills can only read data; your ratings tune them.")}
    <div class="grid g2">${sk.map((s) => `<div class="card"><div style="display:flex;justify-content:space-between;gap:8px"><h2 style="font-size:17px">${esc(s.name)}</h2><span class="pill p-info">${esc(s.category)}</span></div>
      <p class="small muted">${esc(s.description)}</p>
      <div class="grid g4 mt8"><div><div class="small muted">Used</div><b>${s.runs}</b></div><div><div class="small muted">Rating</div><b>${s.avg_score ?? "-"}</b></div><div><div class="small muted">Correct</div><b>${s.accuracy == null ? "-" : Math.round(s.accuracy * 100) + "%"}</b></div><div><div class="small muted">Takes</div><b>${s.avg_analysis_s ?? "-"} s</b></div></div>
      <details class="mini mt8"><summary>Tools (${s.tools.length})</summary><div class="small mono muted">${s.tools.map(esc).join(" · ")}</div></details>
      ${s.lessons.length ? `<div class="small mt8"><b>Learning from feedback</b>${s.lessons.map((l) => `<div class="muted">· ${esc(l)}</div>`).join("")}</div>` : ""}</div>`).join("")}</div></div>`;
}
async function runbooksView() {
  const rbs = await api("/api/runbooks");
  $("#view").innerHTML = `<div class="page">${head("Runbooks", "Fixes that worked and were rated 4-5 stars. When the same problem comes back, the AI reuses them.")}
    ${rbs.length ? `<div class="list">${rbs.map((r) => `<div class="li">${ibox("book", r.enabled ? "var(--c-teal)" : "var(--gray-dot)")}<div class="tx"><div class="t">${esc(r.title)}</div><div class="s2">${esc(r.root_cause)}</div><div class="s">Used ${r.uses}× · rating ${r.score_n ? (r.score_sum / r.score_n).toFixed(1) : "-"} · from <a href="#/problems/${r.source_incident}">P-${r.source_incident}</a></div></div>
      <button class="btn ${r.enabled ? "plain" : "tint"} sm" onclick="toggleRb(${r.id})">${r.enabled ? "Turn off" : "Turn on"}</button></div>`).join("")}</div>` : '<div class="card empty">No runbooks yet. Resolve a problem and rate it 4-5 stars.</div>'}</div>`;
}
window.toggleRb = async (id) => { await api(`/api/runbooks/${id}/toggle`, {method: "POST"}); runbooksView(); };
async function notificationsView() {
  const rows = await api("/api/notifications");
  if (!changed(rows)) return;
  $("#view").innerHTML = `<div class="page">${head("Notifications", "Messages sent to Microsoft Teams. Set the Teams link in Settings.")}
    <div class="list">${rows.map((n) => `<a class="li" href="${n.incident_id ? "#/problems/" + n.incident_id : "#/settings"}">${ltile("teams", "bell", n.status.startsWith("sent") ? "healthy" : "offline")}<div class="tx"><div class="t">${esc(n.event.replace(/_/g, " "))}${n.incident_id ? " · P-" + n.incident_id : ""}</div><div class="s">${esc(n.status)}</div></div><span class="acc">${ago(n.ts)}</span>${chev}</a>`).join("") || '<div class="empty">Nothing sent yet</div>'}</div></div>`;
}
notificationsView.refresh = 10000;

/* ======================= MORE ======================= */
async function deploymentsView() {
  const rows = await api("/api/deployments");
  if (!changed(rows)) return;
  $("#view").innerHTML = `<div class="page">${head("Deployments", "Versions and commits reported by CI. The AI uses them to link a problem to the change behind it.")}
    <div class="list">${rows.map((d) => `<div class="li">${ibox("branch", d.profile === "bad" ? "var(--bad-dot)" : d.author.startsWith("aiops") ? "var(--ok-dot)" : "var(--blue)")}<div class="tx"><div class="t">${esc(d.service)} v${esc(d.version)} <span class="mono muted">${esc(d.commit_hash)}</span></div><div class="s">${esc(d.author)} · ${esc(d.message)}</div></div><span class="acc">${ago(d.ts)}</span></div>`).join("")}</div></div>`;
}
deploymentsView.refresh = 15000;
const SCEN = [
  ["bad_deploy", "Bad release", "alert", "A new payment release (v1.3.0) has a bug. About half of all payments fail.", "finds the bad commit and proposes a rollback to the last good version."],
  ["instance_fault", "One server behind the load balancer breaks", "server", "frontend-b loses its cache; frontend-a stays fine.", "reads the load balancer logs and restarts only frontend-b."],
  ["slow_db", "Slow database", "clock", "Inventory queries take 1.6 s and the connection pool fills up.", "finds where the time goes and proposes restarting inventory."],
  ["cpu_hog", "Runaway job", "cpu", "A batch job eats 3 CPU cores on the server.", "finds the container using the CPU and proposes a restart."],
  ["brute_force", "Password attack", "shield", "One IP tries hundreds of passwords through the firewall.", "confirms it in the firewall and app logs, then proposes blocking the IP."],
];
function chaosView() {
  $("#view").innerHTML = `<div class="page">${head("Demo Scenarios", "Break something on purpose and watch the AI find and fix it. Detection takes about 40 s, the AI another 1-3 minutes.")}
    <div class="list">${SCEN.map(([id, t, ic, what, ai]) => `<div class="li">${ibox(ic, "var(--warn-dot)")}<div class="tx"><div class="t">${t}</div><div class="s2">${what} The AI ${ai}</div></div><button class="btn sm" onclick="chaos('${id}')">Start</button></div>`).join("")}</div>
    <div class="list mt"><div class="li">${ibox("wrench", "var(--gray-dot)")}<div class="tx"><div class="t">Reset everything</div><div class="s">Clears injected faults, the attack and the firewall block list</div></div><button class="btn tint sm" onclick="chaos('reset')">Reset</button></div></div></div>`;
}
window.chaos = async (id) => { try { await api(`/api/chaos/${id}`, {method: "POST"}); toast(id === "reset" ? "Everything reset" : "Started. Opening Problems..."); if (id !== "reset") setTimeout(() => { location.hash = "#/problems"; }, 900); } catch (e) { toast(e.message); } };
async function settingsView() {
  const d = await api("/api/settings"), s = d.settings;
  const f = (k, l, hint = "") => `<div class="li noicon" style="flex-wrap:wrap"><div class="tx" style="min-width:180px"><label class="t" for="s_${k}">${l}</label>${hint ? `<div class="s">${hint}</div>` : ""}</div><input id="s_${k}" value="${esc(s[k])}" style="max-width:220px"></div>`;
  $("#view").innerHTML = `<div class="page" style="max-width:820px">${head("Settings")}
    <div class="sec-h" style="display:flex;align-items:center;gap:6px">${brand("teams", 16, "")}Microsoft Teams</div><div class="list plain"><div class="li noicon" style="flex-wrap:wrap;gap:8px"><div class="tx" style="min-width:100%"><label class="t" for="s_teams_webhook">Teams link (Incoming Webhook or Workflow URL)</label><div class="s">Owners get a card when a problem is found, when a fix needs approval, and when it is resolved.</div></div>
      <input id="s_teams_webhook" value="${esc(s.teams_webhook)}" placeholder="https://...webhook.office.com/..."><button class="btn tint sm" onclick="testTeams()">Send a test message</button></div></div>
    <div class="sec-h">AI</div><div class="list plain">
      <div class="li"><span class="ic logo">${brand("ollama", 20, "Ollama")}</span><div class="tx"><label class="t" for="s_llm_model">Model</label><div class="s">Runs on this server's CPU. Bigger models are slower.</div></div><select id="s_llm_model" style="max-width:220px">${(d.llm.models || [s.llm_model]).map((m) => `<option ${m === s.llm_model ? "selected" : ""}>${esc(m)}</option>`).join("")}</select></div>
      <div class="li noicon"><div class="tx"><div class="t">Investigate new problems automatically</div></div><label class="switch"><input type="checkbox" id="auto_analyze_cb" ${s.auto_analyze === "1" ? "checked" : ""} aria-label="Investigate automatically"><span></span></label></div>
      ${f("verify_after_s", "Check the fix after (seconds)")}</div>
    <div class="sec-h">When to raise a problem</div><div class="list plain">
      ${f("err_threshold", "Error rate", "0.05 = 5% of requests")}${f("p95_threshold_ms", "Response time p95 (ms)")}${f("cpu_threshold", "CPU %")}${f("mem_threshold", "Memory %")}${f("disk_threshold", "Disk %")}${f("auth_fail_per_min", "Failed logins per minute")}</div>
    <button class="btn mt" onclick="saveSettings()">Save</button></div>`;
}
window.saveSettings = async () => {
  const body = {};
  document.querySelectorAll("[id^=s_]").forEach((e) => { body[e.id.slice(2)] = e.value; });
  body.auto_analyze = $("#auto_analyze_cb").checked ? "1" : "0";
  await api("/api/settings", {method: "PUT", body}); toast("Saved");
};
window.testTeams = async () => { await saveSettings(); const r = await api("/api/settings/test-teams", {method: "POST"}); toast("Teams: " + r.status); };

/* ---------- sheet ---------- */
function openModal(html, w) { $("#modal-body").innerHTML = html; $(".modal-box").style.width = w ? `min(${w}px,100%)` : ""; $("#modal").classList.remove("hidden"); }
window.closeModal = () => $("#modal").classList.add("hidden");
$("#modal").addEventListener("click", (e) => { if (e.target.id === "modal") closeModal(); });
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeModal(); });

setInterval(async () => { try { if ((location.hash || "#/") !== "#/") statusBar(await api("/api/overview")); } catch (e) {} }, 20000);
api("/api/overview").then(statusBar).catch(() => {});
route();
