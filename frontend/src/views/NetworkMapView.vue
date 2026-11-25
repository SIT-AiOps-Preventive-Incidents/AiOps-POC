<script setup>
/**
 * Fleet - the machines across your networks (VMs on a hypervisor, cloud instances, servers, devices), drawn
 * as a 2D map in the Service-map style. Internet, the gateway and each network at the top; the machines below,
 * grouped the way you choose (by network, owner, status or whether RadarOps monitors them). Click a machine for
 * its details, and connect the ones you do not monitor yet - straight from here.
 */
import { computed, ref } from "vue";
import { usePageFacts } from "@/composables/usePageFacts";
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

// pick several suggestions and connect them in one go (one shared sign-in)
const picked = ref(new Set());
function toggle(ip) {
  const s = new Set(picked.value);
  s.has(ip) ? s.delete(ip) : s.add(ip);
  picked.value = s;
}
const monitorMany = () => {
  const chosen = (recs.value?.recommendations || []).filter((r) => picked.value.has(r.ip));
  if (!chosen.length) return;
  router.push({ path: "/connect/computer", query: { address: chosen.map((r) => r.ip).join(","), names: chosen.map((r) => r.name).join(",") } });
};

const VW = 1180, PAD = 20, CHIP_W = 176, CHIP_H = 34, GAP = 10, LANE_HEAD = 34, LANE_PAD = 12, BOX_H = 46, HUB_W = 210;
const short = (s) => (s || "").replace(/\.sit\.kmutt\.ac\.th$/i, "");
const GROUPS = [{ value: "network", label: "Network" }, { value: "location", label: "Location" }, { value: "owner", label: "Owner" }, { value: "status", label: "Status" }, { value: "coverage", label: "Monitoring" }];
const KIND = { internet: "Internet", gateway: "Gateway", hub: "Network", connected: "Server on SIT-AIOPS", "virtual machine": "Virtual machine", container: "Container", device: "Device", "random MAC": "Device", service: "Service",
  "cloud instance": "Cloud VM", cloud: "Cloud account" };
const isProblem = (s) => ["problem", "down", "error"].includes(s);
const statusDot = (m) => (isProblem(m.status) || ["agent_silent", "error"].includes(m.cloud?.verdict?.code || m.cloud?.verdict) ? "bad"
  : m.monitored ? "ok" : m.status === "running" ? "info" : "neutral");

// one record per machine (VM / server / device), with the network it sits on and whether RadarOps monitors it
const machines = computed(() => {
  if (!g.value) return [];
  const hubOf = {};
  for (const l of g.value.links) if (l.target.startsWith("hub:")) hubOf[l.source] = l.target.slice(4);
  const cloudHubs = new Set(g.value.nodes.filter((n) => n.kind === "hub" && n.cloud).map((n) => n.label));
  return g.value.nodes.filter((n) => n.id.startsWith("host:") || n.id.startsWith("ip:") || n.kind === "cloud instance").map((n) => ({
    id: n.id, ip: n.ip, mac: n.mac, vendor: n.vendor, label: short(n.label || n.ip), kind: n.kind,
    monitored: !!n.id.startsWith("host:"), owner: n.owner, status: n.status, link: n.link,
    problem_id: n.problem_id, problem_link: n.problem_link, cidr: hubOf[n.id] || "—",
    // cloud: which account, its verdict (machine on but agent silent, stopped in the console, ...)
    cloud: n.kind === "cloud instance" ? { account: n.account, provider: n.provider, zone: n.zone, size: n.size, verdict: n.verdict, public_ip: n.public_ip }
      : n.cloud || (cloudHubs.has(hubOf[n.id]) ? { account: (hubOf[n.id] || "").split(" / ")[0] } : null),
  }));
});
const summary = computed(() => {
  const m = machines.value;
  return { total: m.length, monitored: m.filter((x) => x.monitored).length, unmonitored: m.filter((x) => !x.monitored).length,
    problems: m.filter((x) => isProblem(x.status)).length, networks: new Set(m.map((x) => x.cidr)).size };
});
function groupKey(m) {
  if (group.value === "location") return m.cloud?.account ? `Cloud · ${m.cloud.account}` : "On-premises networks";
  if (group.value === "owner") return m.owner || "No owner";
  if (group.value === "status") return isProblem(m.status) ? "Needs attention" : m.monitored ? "Healthy · monitored" : "Discovered · not monitored";
  if (group.value === "coverage") return m.monitored ? "Monitored by SIT-AIOPS" : "Not monitored yet";
  return m.cidr;
}
const KEY_RANK = { "Needs attention": 0, "Healthy · monitored": 1, "Monitored by SIT-AIOPS": 1, "Discovered · not monitored": 2, "Not monitored yet": 2, "No owner": 9 };

// each number is a door: the drawing on its right says where it goes, and the card goes there
const STATS = computed(() => [
  { k: "Machines", v: summary.value.total, go: "See them all", to: "/network/list", theme: "violet", motif: "rack" },
  { k: "Monitored", v: summary.value.monitored, go: "Open hosts", to: "/computers", theme: "green", motif: "radar" },
  { k: "Not monitored", v: summary.value.unmonitored, go: "Connect them", to: "/network/list", theme: "blue", motif: "plug" },
  { k: "Need attention", v: summary.value.problems, go: "Open incidents", to: "/problems", theme: "rose", motif: "dots" },
  { k: "Networks", v: summary.value.networks, go: "By network", to: "/network/list", theme: "indigo", motif: "mesh" },
]);

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
    boxes.push({ id: hub.id, kind: hub.cloud ? "cloudhub" : "hub", label: hub.label, sub: `${hubCount[hub.label] || 0} machine${(hubCount[hub.label] || 0) === 1 ? "" : "s"}${hub.estimated ? " · estimated" : ""}`, x, y, w: hw, h: BOX_H, node: { ...hub } });
    edges.push(hub.cloud ? { x1: cx, y1: 16 + BOX_H, x2: x + hw / 2, y2: y } : { x1: cx, y1: chainBottom, x2: x + hw / 2, y2: y });
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
const monitor = () => router.push({ path: "/connect/computer", query: { address: selected.value.cloud?.public_ip || selected.value.ip, names: selected.value.label } });
usePageFacts(() => g.value ? {
  known_machines: summary.value.total, monitored_hosts: summary.value.monitored,
  hosts_with_issues: summary.value.problems, networks: summary.value.networks,
  ...(error.value ? { stale_data: 1 } : {}),
} : {});
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader eyebrow="Watch" title="Fleet" subtitle="Every machine you run, on your own networks and in the clouds you rent. Connect the ones you don’t monitor yet, right from the map.">
      <UiButton icon="add" to="/connect/computer">Add a server</UiButton>
      <UiButton variant="tint" icon="cube" to="/network/3d">3D</UiButton>
      <UiButton variant="tint" icon="list" to="/network/list">List</UiButton>
      <UiButton variant="tint" icon="cloud" to="/cloud">Clouds</UiButton>
    </UiPageHeader>

    <nav v-if="g" class="stats" aria-label="Fleet summary">
      <UiStatCard v-for="st in STATS" :key="st.k" :label="st.k" :value="st.v" :sub="st.go" :to="st.to" :theme="st.theme" :motif="st.motif" />
    </nav>
    <section v-if="recs && recs.recommendations.length" v-can="'fleet.connect'" class="recs">
      <div class="recs-head">
        <b>Suggested to monitor next</b>
        <span class="muted small">{{ recs.count }} machine{{ recs.count === 1 ? "" : "s" }} worth connecting · SIT-AIOPS ranked them by what it would learn</span>
        <span v-if="picked.size" class="bulk-btn">
          <UiButton size="sm" variant="ghost" icon="dismiss" @click="picked = new Set()">Clear selection</UiButton>
          <UiButton v-can="'fleet.connect'" size="sm" icon="add" @click="monitorMany">Monitor {{ picked.size }} selected</UiButton>
        </span>
      </div>
      <div class="rec-row">
        <div v-for="r in recs.recommendations.slice(0, 6)" :key="r.ip" :class="['rec', 'spot-host', { checked: picked.has(r.ip) }]"
             role="link" tabindex="0" :aria-label="`Monitor ${short(r.name)}`" @click="monitorIp(r.ip)" @keydown.enter="monitorIp(r.ip)">
          <div class="rec-body">
            <div class="rec-name">{{ short(r.name) }}</div>
            <div class="rec-why muted small">{{ r.reasons[0] }}</div>
            <div class="rec-act">
              <UiButton size="sm" icon="add" @click.stop="monitorIp(r.ip)">Monitor now</UiButton>
              <button type="button" :class="['rec-pick', { on: picked.has(r.ip) }]" :aria-pressed="picked.has(r.ip)" @click.stop="toggle(r.ip)">
                <span class="rec-box"><UiIcon v-if="picked.has(r.ip)" name="checkmark" :size="12" /></span>Select</button>
            </div>
          </div>
          <UiSpot :glyph="r.vendor === 'Proxmox' ? 'vm' : 'server'" hue="sky" badge="plus" :size="72" />
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
            <image :href="`/icons/f/${b.kind === 'hub' ? 'server' : b.kind === 'cloudhub' ? 'cloud' : 'globe'}_regular.svg`" :x="b.x + 14" :y="b.y + b.h / 2 - 9" width="18" height="18" />
            <text :x="b.x + 40" :y="b.y + (b.sub ? 20 : 28)" class="nm">{{ b.label }}</text>
            <text v-if="b.sub" :x="b.x + 40" :y="b.y + 36" class="kd">{{ b.sub }}</text>
          </g>
          <g v-for="c in view.chips" :key="c.id" :class="['chip', { faded: matches && !matches.has(c.id), sel: selected && selected.ip === c.ip, problem: c.dot === 'bad' }]"
             role="button" tabindex="0" @click="pick(c)" @keydown.enter="pick(c)">
            <rect :x="c.x" :y="c.y" :width="c.w" :height="c.h" rx="9" class="cbox" />
            <rect v-if="c.monitored" :x="c.x" :y="c.y" width="3.5" :height="c.h" :class="['acc', { bad: c.dot === 'bad' }]" />
            <circle :cx="c.x + 16" :cy="c.y + c.h / 2" r="4.5" :class="['dot', c.dot]" />
            <text :x="c.x + 28" :y="c.y + c.h / 2 + 4" class="ct">{{ c.label }}</text>
          </g>
        </svg>
        <UiEmpty v-else-if="!error">No machines yet. Add a server, then use “Scan a segment” on the List to find the rest of its network.</UiEmpty>
      </div>
      <aside v-if="selected" class="side">
        <div class="shead"><b>{{ short(selected.label) }}</b><UiButton variant="plain" size="sm" icon="dismiss" aria-label="Close" @click="selected = null" /></div>
        <div class="muted small">{{ KIND[selected.kind] || selected.kind }}<template v-if="selected.estimated"> · estimated</template></div>
        <router-link v-if="selected.problem_link" :to="selected.problem_link" class="alert">
          <span class="dot bad" /> Open incident P-{{ selected.problem_id }} — the AI is on it
        </router-link>
        <dl>
          <template v-if="selected.ip"><dt>IP</dt><dd>{{ selected.ip }}</dd></template>
          <template v-if="selected.cidr && selected.cidr !== '—'"><dt>Network</dt><dd>{{ selected.cidr }}</dd></template>
          <template v-if="selected.mac"><dt>MAC</dt><dd>{{ selected.mac }}</dd></template>
          <template v-if="selected.vendor"><dt>Made by</dt><dd>{{ selected.vendor }}</dd></template>
          <template v-if="selected.owner"><dt>Owner</dt><dd>{{ selected.owner }}</dd></template>
          <template v-if="selected.status"><dt>Status</dt><dd>{{ selected.monitored ? selected.status : selected.cloud ? selected.status : "discovered · not monitored" }}</dd></template>
          <template v-if="selected.cloud?.account"><dt>Cloud</dt><dd>{{ selected.cloud.account }}<template v-if="selected.cloud.zone"> · {{ selected.cloud.zone }}</template></dd></template>
          <template v-if="selected.cloud?.size"><dt>Size</dt><dd>{{ selected.cloud.size }}</dd></template>
          <template v-if="selected.cloud?.public_ip"><dt>Public IP</dt><dd>{{ selected.cloud.public_ip }}</dd></template>
        </dl>
        <p v-if="selected.cloud?.verdict?.text" :class="['verdict', `t-${selected.cloud.verdict.code}`]">{{ selected.cloud.verdict.text }}</p>
        <UiButton v-if="selected.link" size="sm" @click="open">Open</UiButton>
        <UiButton v-can="'fleet.connect'" v-else-if="selected.ip" size="sm" icon="add" @click="monitor">Monitor this machine</UiButton>
      </aside>
    </div>
  </div>
</template>
<style scoped>
/* same vital-signs tiles as the Overview, so the two pages read as one product; each re-groups the map */
.stats { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 16px; margin-bottom: 20px; }
.stat { display: flex; align-items: center; justify-content: space-between; gap: 8px; padding: 18px 14px 18px 22px; background: var(--surface);
  box-shadow: var(--shadow-card); border-radius: 20px; color: var(--c-text); text-decoration: none; transition: transform var(--dur-fast) var(--ease); }
.stat:hover { transform: translateY(-1px); box-shadow: var(--shadow-card), inset 0 0 0 1px color-mix(in srgb, var(--c-primary) 35%, transparent); }
.stat__t { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.stat b { font-size: 34px; font-weight: var(--fw-bold); letter-spacing: -0.03em; line-height: 1.05; font-variant-numeric: tabular-nums; }
.stat span { font-size: var(--fs-sm); color: var(--c-text-2); }
.stat small { font-size: var(--fs-xs); color: var(--c-text-3); margin-top: 8px; }
.stat:hover small { color: var(--c-primary); }
.stat.ok b { color: var(--c-ok-text); } .stat.bad b { color: var(--c-bad-text); }
@media (max-width: 1280px) { .stats { grid-template-columns: repeat(3, 1fr); } }
@media (max-width: 560px) { .stats { grid-template-columns: 1fr; } }
.recs { background: var(--surface); border-radius: 20px; box-shadow: var(--shadow-card); padding: 20px 22px; margin-bottom: 16px; }
.recs-head { display: flex; align-items: baseline; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; } .recs-head b { font-size: var(--fs-xl); }
.bulk-btn { margin-left: auto; align-self: center; display: inline-flex; gap: 8px; }
.rec-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(290px, 1fr)); gap: 12px; align-items: stretch; }
.rec { display: flex; align-items: center; gap: 10px; padding: 16px 12px 16px 18px; border-radius: 16px; background: var(--c-fill);
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.04); cursor: pointer; transition: background var(--dur-fast) var(--ease); }
.rec:hover { background: var(--c-fill-2); }
.rec.checked { box-shadow: inset 0 0 0 1.5px var(--c-primary); }
.rec-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 4px; }
.rec-name { font-weight: var(--fw-semibold); font-size: 15px; overflow-wrap: anywhere; line-height: var(--lh-snug); }
.rec-act { display: flex; align-items: center; gap: 10px; margin-top: 10px; }
.rec-pick { display: inline-flex; align-items: center; gap: 6px; background: none; border: 0; color: var(--c-text-3); font-size: var(--fs-sm); cursor: pointer; padding: 4px; }
.rec-pick:hover, .rec-pick.on { color: var(--c-text); }
.rec-box { width: 16px; height: 16px; border-radius: 5px; display: grid; place-items: center; box-shadow: inset 0 0 0 1.5px var(--c-text-3); }
.rec-pick.on .rec-box { background: var(--c-primary); box-shadow: none; color: var(--c-on-primary); }
.bar { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; }
.search { min-width: 260px; flex: 1; max-width: 360px; } .search :deep(.ui-field) { margin: 0; } .search :deep(label) { display: none; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-items: start; }
.layout.with-side { grid-template-columns: minmax(0, 1fr) 320px; }
@media (max-width: 1080px) { .layout.with-side { grid-template-columns: 1fr; } }
.canvas { background: var(--surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); overflow: auto; padding: 10px; max-height: calc(100vh - 280px); }
svg { display: block; width: 100%; height: auto; }
.edge { fill: none; stroke: var(--c-edge, #c9cfdb); stroke-width: 1.6; }
.lane { fill: var(--c-fill); stroke: var(--c-separator); stroke-dasharray: 5 5; }
.lane-title { font: 600 13px var(--font); fill: var(--c-text); } .lane-sub { font-weight: 400; fill: var(--c-text-2); }
.node { cursor: pointer; } .node .box { fill: var(--c-surface); stroke: var(--c-separator); stroke-width: 1.4; }
.node .box.internet { fill: var(--c-primary-tint); stroke: var(--c-primary); }
.node .box.hub, .node .box.cloudhub { fill: var(--c-primary-tint); stroke: color-mix(in srgb, var(--c-primary) 55%, var(--c-border)); }
.node .box.cloudhub { stroke-dasharray: 5 4; }
.dot.info { fill: var(--c-primary); }
.verdict { margin: 0 0 12px; padding: 9px 11px; border-radius: var(--radius-md); font-size: var(--fs-sm); background: var(--c-fill); color: var(--c-text-2); }
.verdict.t-agent_silent, .verdict.t-error { background: var(--c-bad-bg); color: var(--c-bad-text); }
.verdict.t-stopped_in_cloud { background: var(--c-warn-bg); color: var(--c-warn-text); }
.node .box.gateway { stroke: color-mix(in srgb, var(--c-primary) 45%, var(--c-border)); }
.node:hover .box { stroke: var(--c-primary); }
.nm { font: 600 14px var(--font); fill: var(--c-text); } .kd { font: 11.5px var(--font); fill: var(--c-text-2); }
.chip { cursor: pointer; } .chip .cbox { fill: var(--c-surface); stroke: var(--c-separator); stroke-width: 1; }
.chip:hover .cbox { stroke: var(--c-primary); } .chip.sel .cbox { stroke: var(--c-primary); stroke-width: 2; fill: var(--c-primary-tint); }
.chip.faded { opacity: 0.22; } .acc { fill: var(--c-primary); } .acc.bad { fill: var(--c-bad); }
.chip.problem .cbox { fill: var(--c-bad-bg); stroke: var(--c-bad); animation: chip-alert 1.6s var(--ease, ease) infinite; }
.chip.problem:hover .cbox, .chip.problem.sel .cbox { stroke: var(--c-bad); }
@keyframes chip-alert { 0%, 100% { stroke-opacity: 1; } 50% { stroke-opacity: 0.35; } }
@media (prefers-reduced-motion: reduce) { .chip.problem .cbox { animation: none; } }
.ct { font: 500 12px var(--font); fill: var(--c-text); }
.dot.ok { fill: var(--c-ok); } .dot.bad { fill: var(--c-bad); } .dot.neutral { fill: var(--c-neutral); }
.side { background: var(--surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 14px 16px; position: sticky; top: 12px; }
.shead { display: flex; align-items: center; justify-content: space-between; gap: 8px; } .shead b { font-size: var(--fs-lg); overflow-wrap: anywhere; }
.alert { display: flex; align-items: center; gap: 8px; margin: 12px 0 0; padding: 9px 11px; border-radius: var(--radius-md);
  background: var(--c-bad-bg); color: var(--c-bad-text); font-weight: var(--fw-semibold); font-size: var(--fs-sm); }
.alert .dot { width: 8px; height: 8px; border-radius: 50%; flex: none; } .alert .dot.bad { background: var(--c-bad); }
dl { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 12px 0; font-size: var(--fs-sm); } dt { color: var(--c-text-3); } dd { margin: 0; overflow-wrap: anywhere; }
</style>
