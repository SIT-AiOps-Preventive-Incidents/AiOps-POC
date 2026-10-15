<script setup>
/**
 * Fleet - the machines across your networks (VMs on a hypervisor, cloud instances, servers, devices), drawn
 * as a 2D map in the Service-map style. Internet, the gateway and each network at the top; the machines below,
 * grouped the way you choose (by network, owner, status or whether AIOps monitors them). Click a machine for
 * its details, and connect the ones you do not monitor yet - straight from here.
 */
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";

const router = useRouter();
const g = ref(null);
const error = ref("");
const selected = ref(null);
const query = ref("");
const group = ref("network");
const recs = ref(null);
async function load() {
  try {
    [g.value, recs.value] = [await api.network.graph(), await api.network.recommendations()];
    error.value = "";
  } catch (e) { error.value = e.message; }
}
usePolling(load, 20000);
const monitorIp = (ip) => router.push({ path: "/connect/computer", query: { address: ip } });

const VW = 1180, PAD = 20, CHIP_W = 176, CHIP_H = 34, GAP = 10, LANE_HEAD = 34, LANE_PAD = 12, BOX_H = 46, HUB_W = 210;
const short = (s) => (s || "").replace(/\.sit\.kmutt\.ac\.th$/i, "");
const GROUPS = [{ value: "network", label: "Network" }, { value: "owner", label: "Owner" }, { value: "status", label: "Status" }, { value: "coverage", label: "Monitoring" }];
const KIND = { internet: "Internet", gateway: "Gateway", hub: "Network", connected: "Server on AIOps", "virtual machine": "Virtual machine", container: "Container", device: "Device", "random MAC": "Device", service: "Service" };
const isProblem = (s) => ["problem", "down", "error"].includes(s);
const statusDot = (m) => (isProblem(m.status) ? "bad" : m.monitored && ["healthy", "ok"].includes(m.status) ? "ok" : m.monitored ? "ok" : "neutral");

// one record per machine (VM / server / device), with the network it sits on and whether AIOps monitors it
const machines = computed(() => {
  if (!g.value) return [];
  const hubOf = {};
  for (const l of g.value.links) if (l.target.startsWith("hub:")) hubOf[l.source] = l.target.slice(4);
  return g.value.nodes.filter((n) => n.id.startsWith("host:") || n.id.startsWith("ip:")).map((n) => ({
    id: n.id, ip: n.ip, mac: n.mac, vendor: n.vendor, label: short(n.label || n.ip), kind: n.kind,
    monitored: !!n.id.startsWith("host:"), owner: n.owner, status: n.status, link: n.link, cidr: hubOf[n.id] || "—",
  }));
});
const summary = computed(() => {
  const m = machines.value;
  return { total: m.length, monitored: m.filter((x) => x.monitored).length, unmonitored: m.filter((x) => !x.monitored).length,
    problems: m.filter((x) => isProblem(x.status)).length, networks: new Set(m.map((x) => x.cidr)).size };
});
function groupKey(m) {
  if (group.value === "owner") return m.owner || "No owner";
  if (group.value === "status") return isProblem(m.status) ? "Needs attention" : m.monitored ? "Healthy · monitored" : "Discovered · not monitored";
  if (group.value === "coverage") return m.monitored ? "Monitored by AIOps" : "Not monitored yet";
  return m.cidr;
}
const KEY_RANK = { "Needs attention": 0, "Healthy · monitored": 1, "Monitored by AIOps": 1, "Discovered · not monitored": 2, "Not monitored yet": 2, "No owner": 9 };

const view = computed(() => {
  if (!g.value) return null;
  const nodes = g.value.nodes;
  const gw = nodes.find((n) => n.kind === "gateway");
  const hubs = nodes.filter((n) => n.kind === "hub");
  const boxes = [], lanes = [], chips = [], edges = [];
  const cx = VW / 2;
  let y = 16;
  // --- compact topology header: internet -> gateway -> networks ---
  boxes.push({ id: "internet", kind: "internet", label: "Internet", x: cx - 90, y, w: 180, h: BOX_H, node: { kind: "internet", label: "Internet" } });
  let chainBottom = y + BOX_H; y += BOX_H + 38;
  if (gw) {
    boxes.push({ id: gw.id, kind: "gateway", label: short(gw.label || gw.ip), sub: "Gateway", x: cx - HUB_W / 2, y, w: HUB_W, h: BOX_H, node: gw });
    edges.push({ x1: cx, y1: chainBottom, x2: cx, y2: y }); chainBottom = y + BOX_H; y += BOX_H + 34;
  }
  const hubCount = {}; for (const m of machines.value) hubCount[m.cidr] = (hubCount[m.cidr] || 0) + 1;
  const hw = Math.min(HUB_W, Math.floor((VW - 2 * PAD - (hubs.length - 1) * 20) / Math.max(hubs.length, 1)));
  const rowW = hubs.length * hw + (hubs.length - 1) * 20;
  hubs.forEach((hub, i) => {
    const x = (VW - rowW) / 2 + i * (hw + 20);
    boxes.push({ id: hub.id, kind: "hub", label: hub.label, sub: `${hubCount[hub.label] || 0} machine${(hubCount[hub.label] || 0) === 1 ? "" : "s"}${hub.estimated ? " · estimated" : ""}`, x, y, w: hw, h: BOX_H, node: { ...hub } });
    edges.push({ x1: cx, y1: chainBottom, x2: x + hw / 2, y2: y });
  });
  if (hubs.length) y += BOX_H + 30;

  // --- grouped lanes of machines ---
  const perRow = Math.max(1, Math.floor((VW - 2 * PAD - 2 * LANE_PAD + GAP) / (CHIP_W + GAP)));
  const groups = {};
  for (const m of machines.value) (groups[groupKey(m)] ||= []).push(m);
  const keys = Object.keys(groups).sort((a, b) => (KEY_RANK[a] ?? 5) - (KEY_RANK[b] ?? 5) || groups[b].length - groups[a].length || a.localeCompare(b, undefined, { numeric: true }));
  for (const key of keys) {
    const items = groups[key].sort((a, b) => (a.ip || "").localeCompare(b.ip || "", undefined, { numeric: true }));
    const rows = Math.ceil(items.length / perRow);
    const laneH = LANE_HEAD + rows * (CHIP_H + GAP) - GAP + LANE_PAD;
    const mon = items.filter((m) => m.monitored).length;
    lanes.push({ key, title: key, count: items.length, mon, x: PAD, y, w: VW - 2 * PAD, h: laneH });
    items.forEach((m, i) => {
      const col = i % perRow, row = Math.floor(i / perRow);
      chips.push({ ...m, dot: statusDot(m), x: PAD + LANE_PAD + col * (CHIP_W + GAP), y: y + LANE_HEAD + row * (CHIP_H + GAP), w: CHIP_W, h: CHIP_H });
    });
    y += laneH + 20;
  }
  return { boxes, lanes, chips, edges, W: VW, H: y + 10 };
});

const matches = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return null;
  return new Set((view.value?.chips || []).filter((c) => c.label.toLowerCase().includes(q) || (c.ip || "").includes(q)).map((c) => c.id));
});
const pick = (node) => (selected.value = node);
const open = () => selected.value?.link && router.push(selected.value.link);
const monitor = () => router.push({ path: "/connect/computer", query: { address: selected.value.ip } });
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader title="Fleet" subtitle="Every machine across your networks — VMs, servers and devices. Connect the ones you don’t monitor yet, right from the map.">
      <UiButton icon="add" to="/connect/computer">Add a server</UiButton>
      <UiButton variant="tint" icon="cube" to="/network/3d">3D</UiButton>
      <UiButton variant="tint" icon="list" to="/network/list">List</UiButton>
    </UiPageHeader>

    <div v-if="g" class="stats">
      <div class="stat"><b>{{ summary.total }}</b><span>machines</span></div>
      <div class="stat ok"><b>{{ summary.monitored }}</b><span>monitored</span></div>
      <div class="stat"><b>{{ summary.unmonitored }}</b><span>not monitored</span></div>
      <div :class="['stat', { bad: summary.problems }]"><b>{{ summary.problems }}</b><span>need attention</span></div>
      <div class="stat"><b>{{ summary.networks }}</b><span>networks</span></div>
    </div>
    <section v-if="recs && recs.recommendations.length" class="recs">
      <div class="recs-head"><b>Suggested to monitor next</b><span class="muted small">{{ recs.count }} machine{{ recs.count === 1 ? "" : "s" }} worth connecting · AIOps ranked them by what it would learn</span></div>
      <div class="rec-row">
        <div v-for="r in recs.recommendations.slice(0, 4)" :key="r.ip" class="rec">
          <div class="rec-name">{{ r.name }}</div>
          <div class="rec-why muted small">{{ r.reasons[0] }}</div>
          <UiButton size="sm" icon="add" @click="monitorIp(r.ip)">Monitor</UiButton>
        </div>
      </div>
    </section>
    <div class="bar">
      <UiSegmented v-model="group" :options="GROUPS" label="Group by" />
      <div class="search"><UiField v-model="query" placeholder="Find a machine by name or IP" /></div>
    </div>
    <p v-if="error" class="bad small">{{ error }}</p>

    <div :class="['layout', { 'with-side': selected }]">
      <div class="canvas">
        <svg v-if="view" :viewBox="`0 0 ${view.W} ${view.H}`" role="img" aria-label="Fleet map">
          <path v-for="(e, i) in view.edges" :key="i" :d="`M${e.x1} ${e.y1} C${e.x1} ${(e.y1 + e.y2) / 2} ${e.x2} ${(e.y1 + e.y2) / 2} ${e.x2} ${e.y2}`" class="edge" />
          <g v-for="l in view.lanes" :key="l.key">
            <rect :x="l.x" :y="l.y" :width="l.w" :height="l.h" rx="14" class="lane" />
            <text :x="l.x + 16" :y="l.y + 23" class="lane-title">{{ l.title }} <tspan class="lane-sub">· {{ l.count }}{{ l.mon ? ` · ${l.mon} monitored` : "" }}</tspan></text>
          </g>
          <g v-for="b in view.boxes" :key="b.id" class="node" role="button" tabindex="0" @click="pick(b.node)" @keydown.enter="pick(b.node)">
            <rect :x="b.x" :y="b.y" :width="b.w" :height="b.h" rx="12" :class="['box', b.kind]" />
            <image :href="`/icons/f/${b.kind === 'hub' ? 'server' : 'globe'}_regular.svg`" :x="b.x + 14" :y="b.y + b.h / 2 - 9" width="18" height="18" />
            <text :x="b.x + 40" :y="b.y + (b.sub ? 20 : 28)" class="nm">{{ b.label }}</text>
            <text v-if="b.sub" :x="b.x + 40" :y="b.y + 36" class="kd">{{ b.sub }}</text>
          </g>
          <g v-for="c in view.chips" :key="c.id" :class="['chip', { faded: matches && !matches.has(c.id), sel: selected && selected.ip === c.ip }]"
             role="button" tabindex="0" @click="pick(c)" @keydown.enter="pick(c)">
            <rect :x="c.x" :y="c.y" :width="c.w" :height="c.h" rx="9" class="cbox" />
            <rect v-if="c.monitored" :x="c.x" :y="c.y" width="3.5" :height="c.h" class="acc" />
            <circle :cx="c.x + 16" :cy="c.y + c.h / 2" r="4.5" :class="['dot', c.dot]" />
            <text :x="c.x + 28" :y="c.y + c.h / 2 + 4" class="ct">{{ c.label }}</text>
          </g>
        </svg>
        <UiEmpty v-else-if="!error">No machines yet. Add a server, then use “Scan a segment” on the List to find the rest of its network.</UiEmpty>
      </div>
      <aside v-if="selected" class="side">
        <div class="shead"><b>{{ short(selected.label) }}</b><UiButton variant="plain" size="sm" icon="dismiss" aria-label="Close" @click="selected = null" /></div>
        <div class="muted small">{{ KIND[selected.kind] || selected.kind }}<template v-if="selected.estimated"> · estimated</template></div>
        <dl>
          <template v-if="selected.ip"><dt>IP</dt><dd>{{ selected.ip }}</dd></template>
          <template v-if="selected.cidr && selected.cidr !== '—'"><dt>Network</dt><dd>{{ selected.cidr }}</dd></template>
          <template v-if="selected.mac"><dt>MAC</dt><dd>{{ selected.mac }}</dd></template>
          <template v-if="selected.vendor"><dt>Made by</dt><dd>{{ selected.vendor }}</dd></template>
          <template v-if="selected.owner"><dt>Owner</dt><dd>{{ selected.owner }}</dd></template>
          <template v-if="selected.status"><dt>Status</dt><dd>{{ selected.monitored ? selected.status : "discovered · not monitored" }}</dd></template>
        </dl>
        <UiButton v-if="selected.link" size="sm" @click="open">Open</UiButton>
        <UiButton v-else-if="selected.ip" size="sm" icon="add" @click="monitor">Monitor this machine</UiButton>
      </aside>
    </div>
  </div>
</template>
<style scoped>
.stats { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; }
.stat { background: var(--c-surface); box-shadow: var(--shadow-1); border-radius: var(--radius-lg); padding: 10px 16px; min-width: 96px; }
.stat b { font-size: 24px; display: block; line-height: 1.1; } .stat span { font-size: var(--fs-sm); color: var(--c-text-2); }
.stat.ok b { color: var(--c-ok-text, var(--c-ok)); } .stat.bad b { color: var(--c-bad-text, var(--c-bad)); }
.recs { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 14px 16px; margin-bottom: 14px; }
.recs-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 10px; } .recs-head b { font-size: var(--fs-lg); }
.rec-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap: 10px; }
.rec { border: 1px solid var(--c-separator); border-radius: 12px; padding: 10px 12px; display: flex; flex-direction: column; gap: 4px; }
.rec-name { font-weight: var(--fw-semibold); overflow-wrap: anywhere; } .rec-why { min-height: 32px; } .rec .ui-button { align-self: start; margin-top: 2px; }
.bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.search { min-width: 260px; flex: 1; max-width: 360px; } .search :deep(.ui-field) { margin: 0; } .search :deep(label) { display: none; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-items: start; }
.layout.with-side { grid-template-columns: minmax(0, 1fr) 320px; }
@media (max-width: 1080px) { .layout.with-side { grid-template-columns: 1fr; } }
.canvas { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); overflow: auto; padding: 10px; max-height: calc(100vh - 280px); }
svg { display: block; width: 100%; height: auto; }
.edge { fill: none; stroke: var(--c-edge, #c9cfdb); stroke-width: 1.6; }
.lane { fill: var(--c-fill); stroke: var(--c-separator); stroke-dasharray: 5 5; }
.lane-title { font: 600 13px var(--font); fill: var(--c-text); } .lane-sub { font-weight: 400; fill: var(--c-text-2); }
.node { cursor: pointer; } .node .box { fill: var(--c-surface); stroke: var(--c-separator); stroke-width: 1.4; }
.node .box.internet { fill: var(--c-primary-tint, #eef3ff); stroke: var(--c-primary); }
.node .box.hub { fill: #fff7e6; stroke: #f59e0b; } .node .box.gateway { stroke: #0d1b4c; }
.node:hover .box { stroke: var(--c-primary); }
.nm { font: 600 14px var(--font); fill: var(--c-text); } .kd { font: 11.5px var(--font); fill: var(--c-text-2); }
.chip { cursor: pointer; } .chip .cbox { fill: var(--c-surface); stroke: var(--c-separator); stroke-width: 1; }
.chip:hover .cbox { stroke: var(--c-primary); } .chip.sel .cbox { stroke: var(--c-primary); stroke-width: 2; fill: var(--c-primary-tint, #eef3ff); }
.chip.faded { opacity: 0.22; } .acc { fill: var(--c-primary); }
.ct { font: 500 12px var(--font); fill: var(--c-text); }
.dot.ok { fill: var(--c-ok); } .dot.bad { fill: var(--c-bad); } .dot.neutral { fill: var(--c-neutral, #9aa3b2); }
.side { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 14px 16px; position: sticky; top: 12px; }
.shead { display: flex; align-items: center; justify-content: space-between; gap: 8px; } .shead b { font-size: var(--fs-lg); overflow-wrap: anywhere; }
dl { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 12px 0; font-size: var(--fs-sm); } dt { color: var(--c-text-3); } dd { margin: 0; overflow-wrap: anywhere; }
</style>
