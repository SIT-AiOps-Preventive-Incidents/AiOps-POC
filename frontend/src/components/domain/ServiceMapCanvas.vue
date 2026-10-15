<script setup>
/**
 * Service map canvas (SVG).
 *  - Main flow: everything reachable from "Clients", laid out left to right by call depth.
 *  - Host lanes: services an agent discovered on a computer that are not on the main request path yet,
 *    one lane per computer, so connecting a machine immediately shows what runs on it.
 *  - Test request playback: a dot travels each hop of a real trace, in order, and stamps the time spent there.
 */
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { ms, num, pct, rate } from "@/lib/format";
import { languageLogo, osLogo } from "@/lib/vocab";
import { useMapStore } from "@/stores/map";

const map = useMapStore();
const emit = defineEmits(["select"]);
const W = 168, CW = 190, GAP = 18, TOP = 40, LANE_HEAD = 40, THR = 0.05;
const nodeH = (n) => 58 + (n.instances?.length ? 26 : 0);

const graph = computed(() => {
  const d = map.data;
  if (!d) return null;
  const clients = { id: "clients", name: "Clients", kind: "client", instances: [], hosts: [] };
  // Focus a computer: show ONLY that machine's services (a real service map of that machine), laid out on their
  // own - the rest are not drawn at all, not greyed out. "All" and "Only problems" keep the whole graph.
  const src = map.filter.startsWith("host:") ? d.nodes.filter((n) => n.hosts?.includes(map.filter.slice(5))) : d.nodes;
  const all = [clients, ...src];
  const by = Object.fromEntries(all.map((n) => [n.id, { ...n }]));
  // Clients enter at the public entry point (a service with a test-request URL). Other traced roots - e.g. apps the
  // host agent traces with eBPF - are their own little flows and are drawn inside their computer's lane.
  const publicEntries = d.entry.filter((r) => by[r]?.entry_url);
  const entries = publicEntries.length ? publicEntries : d.entry.filter((r) => by[r]).slice(0, 1);
  const edges = [...d.edges.filter((e) => by[e.from] && by[e.to]),
    ...entries.map((r) => ({ from: "clients", to: r, type: "traced", rps: by[r].rps }))];

  // main flow = reachable from clients
  const main = new Set(["clients"]);
  for (let changed = true; changed;) {
    changed = false;
    for (const e of edges) if (main.has(e.from) && !main.has(e.to)) { main.add(e.to); changed = true; }
  }
  const layerOf = (ids, roots) => {
    const L = Object.fromEntries(roots.map((r) => [r, 0]));
    for (let k = 0; k < 12; k++) for (const e of edges) if (ids.has(e.from) && ids.has(e.to) && L[e.from] != null) L[e.to] = Math.max(L[e.to] ?? 0, L[e.from] + 1);
    for (const id of ids) if (L[id] == null) L[id] = 0;
    return L;
  };
  const place = (ids, L, y0) => {
    const cols = {};
    for (const id of ids) (cols[L[id]] ||= []).push(by[id]);
    const colH = (ns) => ns.reduce((t, n) => t + nodeH(n) + GAP, -GAP);
    const H = Math.max(...Object.values(cols).map(colH));
    for (const [l, ns] of Object.entries(cols)) {
      let y = y0 + (H - colH(ns)) / 2;
      ns.sort((a, b) => a.id.localeCompare(b.id)).forEach((n) => { n.x = 24 + Number(l) * CW; n.y = y; y += nodeH(n) + GAP; });
    }
    return { H, cols: Object.keys(cols).length };
  };

  const mainIds = new Set([...main].filter((id) => by[id]));
  const mainL = layerOf(mainIds, ["clients"]);
  const mainBox = place(mainIds, mainL, TOP);
  let y = TOP + mainBox.H + 36;
  const Wd = Math.max(24 + mainBox.cols * CW, 760);
  const perRow = Math.max(1, Math.floor((Wd - 24) / CW));   // how many chips fit across the canvas

  // host lanes: services an agent discovered on a computer that are not on the main request path. They are
  // mostly independent, so wrap them into a grid that fills the width instead of one tall column.
  const rest = all.filter((n) => !main.has(n.id) && n.kind !== "client");
  const lanes = {};
  for (const n of rest) (lanes[n.hosts?.[0] || "unknown host"] ||= []).push(n.id);
  const laneBoxes = [];
  for (const [host, ids] of Object.entries(lanes)) {
    const list = ids.map((id) => by[id]).sort((a, b) => a.id.localeCompare(b.id));
    const top = y + LANE_HEAD;
    let gx = 24, gy = top, rowH = 0, col = 0, bottom = top;
    for (const n of list) {
      n.x = gx; n.y = gy;
      bottom = Math.max(bottom, gy + nodeH(n));
      rowH = Math.max(rowH, nodeH(n));
      if (++col >= perRow) { gy += rowH + GAP; gx = 24; rowH = 0; col = 0; } else gx += CW;
    }
    const h = d.hosts.find((x) => x.name === host);
    laneBoxes.push({ host, os: h?.os, y, h: (bottom - top) + LANE_HEAD + 16, count: ids.length });
    y += (bottom - top) + LANE_HEAD + 30;
  }
  return { by, edges, mainIds, nodes: all.map((n) => by[n.id]), mainLayers: Math.max(...Object.values(mainL)) + 1, laneBoxes, W: Wd, H: y + 10 };
});

const bad = (n) => !!n.problem_id || (n.error_rate ?? 0) > THR || (n.instances || []).some((i) => i.problem_id || i.error_rate > THR);
const focus = computed(() => {
  const g = graph.value;
  // host focus now subsets the whole graph (above), so nothing to fade; only "Only problems" dims the off-path nodes
  if (!g || map.filter === "all" || map.filter.startsWith("host:")) return null;
  const keep = new Set();
  const up = (id) => { if (keep.has(id)) return; keep.add(id); g.edges.filter((e) => e.to === id).forEach((e) => up(e.from)); };
  g.nodes.filter(bad).forEach((n) => up(n.id));
  return keep;
});

function geom(e) {
  const g = graph.value, a = g.by[e.from], b = g.by[e.to];
  if (!a || a.x == null || !b || b.x == null) return null;
  const x1 = a.x + W, y1 = a.y + nodeH(a) / 2, x2 = b.x - 4, y2 = b.y + nodeH(b) / 2;
  const back = x2 < x1; // edge going left (rare): route as a gentle S curve
  const mx = back ? x1 + 60 : (x1 + x2) / 2;
  return { x1, y1, x2, y2, mx, mx2: back ? x2 - 60 : mx, d: `M${x1} ${y1} C${mx} ${y1} ${back ? x2 - 60 : mx} ${y2} ${x2} ${y2}` };
}
const edgeViews = computed(() => (graph.value?.edges || [])
  // Only draw the request flow (main path). Services discovered on a computer are shown as a grid
  // inside their host lane, not a flow - drawing their edges across that grid just makes spaghetti.
  .filter((e) => graph.value.mainIds.has(e.from) && graph.value.mainIds.has(e.to))
  .map((e) => {
  const gm = geom(e);
  if (!gm) return null;
  const sel = map.selected && (e.from === map.selected || e.to === map.selected);
  const faded = (focus.value && !(focus.value.has(e.from) && focus.value.has(e.to))) || (map.selected && !sel);
  return { ...e, ...gm, key: `${e.from}>${e.to}`, bad: (e.error_rate ?? 0) > THR, sel, faded };
}).filter(Boolean));

// "frontend-a" -> "a", "CP26PT1.sit.kmutt.ac.th:3133630" -> "pid 3133630"; clipped to the chip width
function chipLabel(n, inst) {
  let id = inst.id.replace(`${n.id}-`, "");
  const pid = id.match(/:(\d+)$/);
  if (pid && id.includes(".")) id = `pid ${pid[1]}`;
  const text = `${id} · ${Math.round((inst.rps / (n.rps || 1)) * 100)}%`;
  const max = Math.floor(((W - 24 - (n.instances.length - 1) * 6) / n.instances.length - 12) / 6.2);
  return text.length > max ? `${text.slice(0, Math.max(max - 1, 3))}…` : text;
}

const kindText = (n) => n.kind === "client" ? "Users on the internet" : n.kind === "network" ? (n.id.includes("firewall") ? "Firewall" : "Load balancer")
  : n.kind === "process" ? `Discovered on ${n.hosts?.[0] || "-"}` : n.kind === "external" ? "External dependency" : `Service · ${n.owner || "no owner"}`;
const metric = (n) => n.kind === "client" ? "" : n.rps != null ? `${rate(n.rps)} · ${pct(n.error_rate)}`
  : n.kind === "process" || n.kind === "external" ? (n.seen_recently ? "running · not traced" : "not seen recently") : "no traffic yet";
const logoOf = (n) => n.kind === "client" ? null : languageLogo(n.kind === "network" ? "nginx" : n.language || n.id);

// ---------------- test request playback ----------------
const visited = ref({});      // node id -> { ms, error }
const visitedInst = ref({});  // instance id -> true
const dot = ref(null);        // { x, y, error }
let raf = 0;
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const bez = (g, t) => {
  const u = 1 - t, X = [g.x1, g.mx, g.mx2, g.x2], Y = [g.y1, g.y1, g.y2, g.y2];
  const c = (p) => u * u * u * p[0] + 3 * u * u * t * p[1] + 3 * u * t * t * p[2] + t * t * t * p[3];
  return { x: c(X), y: c(Y) };
};
function play(hops) {
  cancelAnimationFrame(raf);
  visited.value = {}; visitedInst.value = {}; dot.value = null;
  const steps = hops.map((h) => ({ h, g: geom({ from: h.from, to: h.to }) })).filter((s) => s.g);
  if (reduced) { steps.forEach(({ h }, i) => arrive(h, i)); map.test.step = steps.length; map.test.phase = "done"; return; }
  const HOP_MS = 650;
  let i = 0, t0 = performance.now();
  const frame = (now) => {
    if (i >= steps.length) { dot.value = null; map.test.phase = "done"; return; }
    const { h, g } = steps[i];
    const t = Math.min((now - t0) / HOP_MS, 1), e = 1 - Math.pow(1 - t, 3);
    dot.value = { ...bez(g, e), error: h.error };
    map.test.step = i;
    if (t >= 1) { arrive(h, i); i += 1; t0 = now + 120; }
    raf = requestAnimationFrame(frame);
  };
  raf = requestAnimationFrame(frame);
}
function arrive(h) {
  visited.value = { ...visited.value, [h.to]: { ms: h.duration, error: h.error } };
  if (h.instance) visitedInst.value = { ...visitedInst.value, [h.instance]: true };
}
watch(() => map.test.phase, (p) => { if (p === "playing") play(map.test.hops); if (p === "idle") { visited.value = {}; visitedInst.value = {}; dot.value = null; } });
onBeforeUnmount(() => cancelAnimationFrame(raf));
</script>

<template>
  <div class="canvas">
    <svg v-if="graph" :viewBox="`0 0 ${graph.W} ${graph.H}`" :width="graph.W" :height="graph.H" role="img" aria-label="Service map">
      <defs>
        <marker v-for="[id, c] in [['a', 'var(--c-edge)'], ['ab', 'var(--c-bad)'], ['as', 'var(--c-primary)']]" :id="`m-${id}`" :key="id" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 1 9 5 0 9z" :style="{ fill: c }" /></marker>
        <filter id="glow"><feGaussianBlur stdDeviation="3" /></filter>
      </defs>
      <text v-for="l in graph.mainLayers" :key="l" :x="24 + (l - 1) * CW" y="22" class="lane-label">{{ ["Clients", "Perimeter", "Load balancing", "Web", "Application", "Backend", "Data"][l - 1] || `Tier ${l}` }}</text>

      <!-- host lanes -->
      <g v-for="lane in graph.laneBoxes" :key="lane.host">
        <rect x="12" :y="lane.y" :width="graph.W - 24" :height="lane.h" rx="14" class="lane" />
        <image v-if="osLogo(lane.os)" :class="{ 'ui-logo--mono': osLogo(lane.os) === 'apple' }" :href="`/icons/b/${osLogo(lane.os)}.svg`" x="26" :y="lane.y + 11" width="16" height="16" />
        <text :x="osLogo(lane.os) ? 48 : 26" :y="lane.y + 24" class="lane-title">{{ lane.host }} <tspan class="lane-sub">· {{ lane.count }} {{ lane.count === 1 ? "service" : "services" }} not on the traced request path</tspan></text>
      </g>

      <!-- edges -->
      <g v-for="e in edgeViews" :key="e.key">
        <path :d="e.d" :class="['edge', { bad: e.bad, sel: e.sel, faded: e.faded, net: e.type === 'network' }]" :marker-end="`url(#m-${e.bad ? 'ab' : e.sel ? 'as' : 'a'})`">
          <title>{{ e.from }} to {{ e.to }}{{ e.rps != null ? `: ${rate(e.rps)}` : " (seen on the network)" }}</title>
        </path>
        <!-- Only label an edge that actually carries traffic (or is failing). Stamping "0.0/s" on every
             edge of a selected hub just stacks up into unreadable clutter - the rate per caller/callee is
             in the side panel's Calls / Called by lists anyway. -->
        <text v-if="(e.sel || e.bad) && !e.faded && e.rps != null && (e.bad || e.rps >= 0.05)" :x="e.mx" :y="(e.y1 + e.y2) / 2 - 7" text-anchor="middle" :class="['edge-label', { bad: e.bad }]">{{ num(e.rps) }}/s{{ e.bad ? ` · ${pct(e.error_rate, 0)}` : "" }}</text>
      </g>

      <!-- nodes -->
      <g v-for="n in graph.nodes.filter((x) => x.x != null)" :key="n.id"
         :class="['node', { bad: bad(n), sel: map.selected === n.id, faded: focus && !focus.has(n.id) && n.id !== 'clients', disc: n.kind === 'process' || n.kind === 'external', hit: visited[n.id] }]"
         role="button" :aria-label="n.name" tabindex="0" @click="emit('select', n.id)" @keydown.enter="emit('select', n.id)" @keydown.space.prevent="emit('select', n.id)">
        <rect class="box" :x="n.x" :y="n.y" :width="W" :height="nodeH(n)" rx="11" />
        <circle :cx="n.x + 20" :cy="n.y + 20" r="13" class="logo-bg" />
        <image v-if="logoOf(n)" :href="`/icons/b/${logoOf(n)}.svg`" :x="n.x + 12" :y="n.y + 12" width="16" height="16" />
        <image v-else :href="`/icons/f/${n.kind === 'client' ? 'globe' : n.kind === 'external' ? 'database' : 'apps'}_regular.svg`" :x="n.x + 12" :y="n.y + 12" width="16" height="16" />
        <circle v-if="n.kind !== 'client'" :cx="n.x + 31" :cy="n.y + 10" r="4" :class="['sdot', bad(n) ? 'bad' : n.rps != null || n.seen_recently ? 'ok' : 'off']" />
        <foreignObject :x="n.x + 38" :y="n.y + 7" :width="W - 46" :height="n.instances?.length ? 42 : nodeH(n) - 12">
          <div class="nd" xmlns="http://www.w3.org/1999/xhtml">
            <div class="nd-nm">{{ n.id === "clients" ? "Clients" : n.id }}</div>
            <div class="nd-kd">{{ kindText(n) }}</div>
            <div v-if="metric(n) || n.problem_id" :class="['nd-kp', { bad: bad(n) }]">{{ metric(n) }}{{ n.problem_id ? ` · P-${n.problem_id}` : "" }}</div>
          </div>
        </foreignObject>
        <g v-for="(inst, k) in n.instances" :key="inst.id" :class="['chip', { bad: inst.error_rate > THR || inst.problem_id, hit: visitedInst[inst.id] }]"
           :transform="`translate(${n.x + 10 + k * ((W - 20 - (n.instances.length - 1) * 5) / n.instances.length + 5)}, ${n.y + nodeH(n) - 28})`">
          <rect :width="(W - 20 - (n.instances.length - 1) * 5) / n.instances.length" height="22" rx="6" />
          <text x="7" y="15">{{ chipLabel(n, inst) }}</text>
        </g>
        <g v-if="visited[n.id]" :transform="`translate(${n.x + W - 8}, ${n.y - 8})`">
          <rect :x="-60" y="0" width="64" height="20" rx="10" :class="['stamp', { bad: visited[n.id].error }]" />
          <text x="-28" y="14" text-anchor="middle" class="stamp-t">{{ ms(visited[n.id].ms) }}</text>
        </g>
      </g>

      <g v-if="dot" class="dot">
        <circle :cx="dot.x" :cy="dot.y" r="11" :class="['halo', { bad: dot.error }]" filter="url(#glow)" />
        <circle :cx="dot.x" :cy="dot.y" r="6" :class="['core', { bad: dot.error }]" />
      </g>
    </svg>
  </div>
</template>

<style scoped>
.canvas { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); overflow: auto; padding: 8px; }
/* render at natural pixel size so a node is always the same size; scroll if the graph is wider than the card
   (never stretch a small graph to fill the width, which blew the boxes up) */
svg { display: block; max-width: 100%; height: auto; }
.lane-label { font: 500 12px var(--font); fill: var(--c-text-3); }
.lane { fill: var(--c-fill); stroke: var(--c-separator); stroke-dasharray: 5 5; }
.lane-title { font: 600 13px var(--font); fill: var(--c-text); }
.lane-sub { font-weight: 400; fill: var(--c-text-2); }
.edge { fill: none; stroke: var(--c-edge); stroke-width: 2; transition: opacity var(--dur); }
.edge.net { stroke-dasharray: 5 4; }
.edge.bad { stroke: var(--c-bad); stroke-width: 2; }
.edge.sel { stroke: var(--c-primary); stroke-width: 2.2; }
.edge.faded { opacity: 0.18; }
.edge-label { font: 600 11px var(--font); fill: var(--c-primary); }
.edge-label.bad { fill: var(--c-bad-text); }
.node { cursor: pointer; transition: opacity var(--dur); }
.node .box { fill: var(--c-surface); stroke: var(--c-border); stroke-width: 1.25; }
.node:hover .box, .node:focus-visible .box { stroke: var(--c-primary); }
.node.disc .box { stroke-dasharray: 5 4; stroke: var(--c-edge-disc); }
.node.sel .box { stroke: var(--c-primary); stroke-width: 2; }
.node.bad .box { stroke: var(--c-bad); stroke-width: 1.5; fill: var(--c-bad-surface); }
.node.hit .box { stroke: var(--c-primary); stroke-width: 2.2; fill: var(--c-primary-tint); }
.node.faded { opacity: 0.25; }
.node:focus { outline: none; }
.node:focus-visible .box { stroke-width: 2.5; }
.logo-bg { fill: var(--c-logo-bg); stroke: var(--c-separator); stroke-width: 0.5; }
.sdot { stroke: var(--c-surface); stroke-width: 2; }
.sdot.ok { fill: var(--c-ok); } .sdot.bad { fill: var(--c-bad); } .sdot.off { fill: var(--c-neutral); }
/* node text in a foreignObject so a long service name wraps to two lines instead of overflowing */
.nd { display: flex; flex-direction: column; gap: 1px; overflow: hidden; }
.nd-nm { font: 600 12px/1.2 var(--font); color: var(--c-text); word-break: break-word; overflow-wrap: anywhere;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.nd-kd { font: 10.5px/1.25 var(--font); color: var(--c-text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.nd-kp { font: 500 10.5px/1.3 var(--font); color: var(--c-text-2); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; margin-top: 1px; }
.nd-kp.bad { color: var(--c-bad-text); }
.chip rect { fill: var(--c-fill); transition: fill var(--dur); }
.chip.bad rect { fill: var(--c-bad-bg); }
.chip.hit rect { fill: var(--c-primary-tint-2); }
.chip text { font: 500 10px var(--font); fill: var(--c-text); }
.stamp { fill: var(--c-primary); }
.stamp.bad { fill: var(--c-bad); }
.stamp-t { font: 700 11px var(--font); fill: #fff; }
.halo { fill: var(--c-halo); } .halo.bad { fill: var(--c-halo-bad); }
.core { fill: var(--c-primary); stroke: var(--c-surface); stroke-width: 2; } .core.bad { fill: var(--c-bad); }
</style>
