<script setup>
/**
 * Service map canvas (SVG).
 *  - Main flow: everything reachable from "Clients", laid out left to right by call depth.
 *  - Host lanes: services an agent discovered on a computer that are not on the main request path yet,
 *    one lane per computer, so connecting a machine immediately shows what runs on it.
 *  - Test request playback: a dot travels each hop of a real trace, in order, and stamps the time spent there.
 */
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { ms, num, pct } from "@/lib/format";
import { languageLogo, osLogo } from "@/lib/vocab";
import { useMapStore } from "@/stores/map";

const map = useMapStore();
const emit = defineEmits(["select"]);
const W = 196, CW = 240, GAP = 22, TOP = 40, LANE_HEAD = 40, THR = 0.05;
const nodeH = (n) => 66 + (n.instances?.length ? 30 : 0);

const graph = computed(() => {
  const d = map.data;
  if (!d) return null;
  const clients = { id: "clients", name: "Clients", kind: "client", instances: [], hosts: [] };
  const all = [clients, ...d.nodes];
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
  let y = TOP + mainBox.H + 36, width = mainBox.cols;

  // host lanes for discovered services that are not on the main path
  const rest = all.filter((n) => !main.has(n.id) && n.kind !== "client");
  const lanes = {};
  for (const n of rest) (lanes[n.hosts?.[0] || "unknown host"] ||= []).push(n.id);
  const laneBoxes = [];
  for (const [host, ids] of Object.entries(lanes)) {
    const set = new Set(ids);
    const roots = ids.filter((id) => !edges.some((e) => e.to === id && set.has(e.from)));
    const box = place(set, layerOf(set, roots), y + LANE_HEAD);
    const h = d.hosts.find((x) => x.name === host);
    laneBoxes.push({ host, os: h?.os, y, h: box.H + LANE_HEAD + 16, count: ids.length });
    width = Math.max(width, box.cols);
    y += box.H + LANE_HEAD + 30;
  }
  const Wd = Math.max(24 + width * CW, 760);
  return { by, edges, nodes: all.map((n) => by[n.id]), mainLayers: Math.max(...Object.values(mainL)) + 1, laneBoxes, W: Wd, H: y + 10 };
});

const bad = (n) => !!n.problem_id || (n.error_rate ?? 0) > THR || (n.instances || []).some((i) => i.problem_id || i.error_rate > THR);
const focus = computed(() => {
  const g = graph.value;
  if (!g || map.filter === "all") return null;
  if (map.filter.startsWith("host:")) {
    const host = map.filter.slice(5);
    return new Set(g.nodes.filter((n) => n.hosts?.includes(host)).map((n) => n.id));
  }
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
const edgeViews = computed(() => (graph.value?.edges || []).map((e) => {
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
const metric = (n) => n.kind === "client" ? "" : n.rps != null ? `${num(n.rps)} req/s · ${pct(n.error_rate)} errors`
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
    <svg v-if="graph" :viewBox="`0 0 ${graph.W} ${graph.H}`" :style="{ minWidth: `${Math.min(graph.W, 860)}px` }" role="img" aria-label="Service map">
      <defs>
        <marker v-for="[id, c] in [['a', 'var(--c-edge)'], ['ab', 'var(--c-bad)'], ['as', 'var(--c-primary)']]" :id="`m-${id}`" :key="id" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 1 9 5 0 9z" :style="{ fill: c }" /></marker>
        <filter id="glow"><feGaussianBlur stdDeviation="3" /></filter>
      </defs>
      <text v-for="l in graph.mainLayers" :key="l" :x="24 + (l - 1) * CW" y="22" class="lane-label">{{ ["CLIENTS", "PERIMETER", "LOAD BALANCING", "WEB", "APPLICATION", "BACKEND", "DATA"][l - 1] || `TIER ${l}` }}</text>

      <!-- host lanes -->
      <g v-for="lane in graph.laneBoxes" :key="lane.host">
        <rect x="12" :y="lane.y" :width="graph.W - 24" :height="lane.h" rx="14" class="lane" />
        <image v-if="osLogo(lane.os)" :class="{ 'ui-logo--mono': osLogo(lane.os) === 'apple' }" :href="`/icons/b/${osLogo(lane.os)}.svg`" x="26" :y="lane.y + 11" width="16" height="16" />
        <text :x="osLogo(lane.os) ? 48 : 26" :y="lane.y + 24" class="lane-title">{{ lane.host }} <tspan class="lane-sub">· {{ lane.count }} {{ lane.count === 1 ? "service" : "services" }} outside the shop request path</tspan></text>
      </g>

      <!-- edges -->
      <g v-for="e in edgeViews" :key="e.key">
        <path :d="e.d" :class="['edge', { bad: e.bad, sel: e.sel, faded: e.faded, net: e.type === 'network' }]" :marker-end="`url(#m-${e.bad ? 'ab' : e.sel ? 'as' : 'a'})`">
          <title>{{ e.from }} to {{ e.to }}{{ e.rps != null ? `: ${num(e.rps, 2)} req/s` : " (seen on the network)" }}</title>
        </path>
        <text v-if="(e.sel || e.bad) && !e.faded && e.rps != null" :x="e.mx" :y="(e.y1 + e.y2) / 2 - 7" text-anchor="middle" :class="['edge-label', { bad: e.bad }]">{{ num(e.rps) }}/s{{ e.bad ? ` · ${pct(e.error_rate, 0)}` : "" }}</text>
      </g>

      <!-- nodes -->
      <g v-for="n in graph.nodes.filter((x) => x.x != null)" :key="n.id"
         :class="['node', { bad: bad(n), sel: map.selected === n.id, faded: focus && !focus.has(n.id) && n.id !== 'clients', disc: n.kind === 'process' || n.kind === 'external', hit: visited[n.id] }]"
         role="button" :aria-label="n.name" tabindex="0" @click="emit('select', n.id)" @keydown.enter="emit('select', n.id)" @keydown.space.prevent="emit('select', n.id)">
        <rect class="box" :x="n.x" :y="n.y" :width="W" :height="nodeH(n)" rx="14" />
        <circle :cx="n.x + 24" :cy="n.y + 24" r="14" class="logo-bg" />
        <image v-if="logoOf(n)" :href="`/icons/b/${logoOf(n)}.svg`" :x="n.x + 15" :y="n.y + 15" width="18" height="18" />
        <image v-else :href="`/icons/f/${n.kind === 'client' ? 'globe' : n.kind === 'external' ? 'database' : 'apps'}_regular.svg`" :x="n.x + 15" :y="n.y + 15" width="18" height="18" />
        <circle v-if="n.kind !== 'client'" :cx="n.x + 35" :cy="n.y + 13" r="4.5" :class="['sdot', bad(n) ? 'bad' : n.rps != null || n.seen_recently ? 'ok' : 'off']" />
        <text :x="n.x + 46" :y="n.y + 22" class="nm">{{ n.id === "clients" ? "Clients" : n.id }}</text>
        <text :x="n.x + 46" :y="n.y + 38" class="kd">{{ kindText(n) }}</text>
        <text :x="n.x + 14" :y="n.y + 57" :class="['kp', { bad: bad(n) }]">{{ metric(n) }}{{ n.problem_id ? ` · P-${n.problem_id}` : "" }}</text>
        <g v-for="(inst, k) in n.instances" :key="inst.id" :class="['chip', { bad: inst.error_rate > THR || inst.problem_id, hit: visitedInst[inst.id] }]"
           :transform="`translate(${n.x + 12 + k * ((W - 24 - (n.instances.length - 1) * 6) / n.instances.length + 6)}, ${n.y + 64})`">
          <rect :width="(W - 24 - (n.instances.length - 1) * 6) / n.instances.length" height="24" rx="7" />
          <text x="8" y="16">{{ chipLabel(n, inst) }}</text>
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
svg { display: block; width: 100%; height: auto; }
.lane-label { font: 600 11px var(--font); fill: var(--c-text-3); letter-spacing: 0.06em; }
.lane { fill: var(--c-fill); stroke: var(--c-separator); stroke-dasharray: 5 5; }
.lane-title { font: 600 13px var(--font); fill: var(--c-text); }
.lane-sub { font-weight: 400; fill: var(--c-text-2); }
.edge { fill: none; stroke: var(--c-edge); stroke-width: 1.6; transition: opacity var(--dur); }
.edge.net { stroke-dasharray: 5 4; }
.edge.bad { stroke: var(--c-bad); stroke-width: 2; }
.edge.sel { stroke: var(--c-primary); stroke-width: 2.2; }
.edge.faded { opacity: 0.18; }
.edge-label { font: 600 11px var(--font); fill: var(--c-primary); }
.edge-label.bad { fill: var(--c-bad-text); }
.node { cursor: pointer; transition: opacity var(--dur); }
.node .box { fill: var(--c-surface); stroke: var(--c-separator); stroke-width: 1; }
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
.nm { font: 600 13.5px var(--font); fill: var(--c-text); }
.kd { font: 12px var(--font); fill: var(--c-text-2); }
.kp { font: 500 12px var(--font); fill: var(--c-text-2); }
.kp.bad { fill: var(--c-bad-text); }
.chip rect { fill: var(--c-fill); transition: fill var(--dur); }
.chip.bad rect { fill: var(--c-bad-bg); }
.chip.hit rect { fill: var(--c-primary-tint-2); }
.chip text { font: 500 11px var(--font); fill: var(--c-text); }
.stamp { fill: var(--c-primary); }
.stamp.bad { fill: var(--c-bad); }
.stamp-t { font: 700 11px var(--font); fill: #fff; }
.halo { fill: var(--c-halo); } .halo.bad { fill: var(--c-halo-bad); }
.core { fill: var(--c-primary); stroke: var(--c-surface); stroke-width: 2; } .core.bad { fill: var(--c-bad); }
</style>
