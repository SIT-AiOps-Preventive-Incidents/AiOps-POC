<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { ago } from "@/lib/format";
import { BOX, LAYERS, glyph, layout, roleLabel, statusLabel, tone } from "@/lib/netlayout";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const topo = ref(null);
const error = ref("");
const route = useRoute();
const router = useRouter();
const tab = ref(["map", "assets", "events"].includes(route.query.tab) ? route.query.tab : "map");
watch(tab, (t) => router.replace({ query: t === "map" ? {} : { tab: t } }));
const selected = ref(null);
const scanning = ref(false);

async function load() {
  try { topo.value = await api.network.get(); error.value = ""; } catch (e) { error.value = e.message; }
}
usePolling(load, 15000);

async function scanNow() {
  scanning.value = true;
  try { topo.value = await api.network.scan(); ui.toast("Scan finished"); } catch (e) { ui.toast(e.message); } finally { scanning.value = false; }
}

const view = computed(() => layout(topo.value));
const colCount = computed(() => [0, 1, 2, 3].map((l) => nodes.value.filter((n) => n.layer === l).length));
const nodes = computed(() => topo.value?.nodes || []);
const devices = computed(() => nodes.value.filter((n) => n.kind === "device"));
const answering = computed(() => devices.value.filter((d) => !["unreachable", "not polled"].includes(d.status)));
const hosts = computed(() => nodes.value.filter((n) => n.kind === "host"));
const cablesDown = computed(() => (topo.value?.links || []).filter((l) => l.kind === "cable" && l.status === "down"));
const unknown = computed(() => hosts.value.filter((h) => !h.known && h.status !== "missing"));
const impacted = computed(() => topo.value?.impacted_services || []);
const empty = computed(() => topo.value && !(topo.value.sources || []).length);
const sel = computed(() => nodes.value.find((n) => n.id === selected.value));
const selLinks = computed(() => (topo.value?.links || []).filter((l) => l.a === selected.value || l.b === selected.value));
const nameOf = (id) => nodes.value.find((n) => n.id === id)?.name || id;
const kindLabel = { device: "Network device", host: "Host", service: "Service" };
const sevTone = { critical: "bad", warning: "action", info: "info" };
const tabs = [{ value: "map", label: "Topology" }, { value: "assets", label: "Assets" }, { value: "events", label: "Changes" }];
const short = (s, n = 24) => (s && s.length > n ? `${s.slice(0, n - 1)}…` : s || "");

function subtitle(n) {
  if (n.kind === "device") {
    const ports = (n.ports || []).filter((p) => !p.mgmt);
    const down = ports.filter((p) => !p.up).length;
    return `${n.ip || "-"} · ${down ? `${down}/${ports.length} down` : `${ports.length} ports`}`;
  }
  if (n.kind === "host") return `${n.ip} · ${n.attached || ""}`;
  return "service";
}
const tileIcon = (n) => (n.kind === "device" ? "developer_board" : n.kind === "host" ? "server" : "cube");
</script>

<template>
  <div class="page page--wide">
    <UiPageHeader title="Network" subtitle="What the switches and routers see, from the core down to the services. Found over SNMP and LLDP every minute.">
      <UiButton icon="arrow_sync" :loading="scanning" :disabled="empty" @click="scanNow">Scan now</UiButton>
    </UiPageHeader>

    <UiCard v-if="error" class="mb"><p class="bad-text">Could not load the network: {{ error }}</p></UiCard>

    <UiCard v-else-if="empty">
      <UiEmpty>
        <b>No network devices yet.</b>
        <p class="small mt-2">AIOps One finds switches and routers in two ways: containers labelled <code>aiops.netdevice=true</code>
          (start the demo lab with <code>netlab/up.sh</code>), or the addresses you list under Settings → Network devices.
          They need SNMP v2c read access; LLDP is used to find the cables between them.</p>
      </UiEmpty>
    </UiCard>

    <template v-else-if="topo">
      <div class="grid grid--4 tiles">
        <UiTile label="Network devices" :value="`${answering.length} / ${devices.length}`" hint="answering SNMP"
                :tone="devices.some((d) => d.status === 'unreachable') ? 'bad' : undefined" />
        <UiTile label="Links down" :value="cablesDown.length" :hint="cablesDown.length ? short(cablesDown[0].id, 34) : 'every cable is up'"
                :tone="cablesDown.length ? 'bad' : undefined" />
        <UiTile label="Hosts on the network" :value="hosts.filter((h) => h.status !== 'missing').length"
                :hint="unknown.length ? `${unknown.length} unknown` : 'all known to AIOps One'" :tone="unknown.length ? 'action' : undefined" />
        <UiTile label="Services cut off" :value="impacted.length" :hint="impacted.length ? impacted.join(', ') : 'all reachable from the core'"
                :tone="impacted.length ? 'bad' : undefined" />
      </div>

      <div class="toolbar">
        <UiSegmented v-model="tab" :options="tabs" label="Network view" />
        <span class="small muted">Discovery: SNMP v2c (IF-MIB, IP-MIB, LLDP-MIB) · {{ (topo.sources || []).length }} devices polled · last scan {{ ago(topo.ts) }}</span>
      </div>

      <!-- ---------------- topology ---------------- -->
      <div v-if="tab === 'map'" :class="['layout', { 'with-side': sel }]">
        <UiCard class="canvas-card">
          <div class="canvas" role="img" :aria-label="`Network topology with ${nodes.length} items`">
            <svg :viewBox="`-4 0 ${view.width + 8} ${view.height}`" :width="view.width + 8" :height="view.height">
              <g v-for="(l, i) in LAYERS" :key="l">
                <text :x="i * BOX.col" y="14" class="col-label">{{ l }}<tspan class="col-count"> · {{ colCount[i] }}</tspan></text>
                <line :x1="i * BOX.col" :x2="i * BOX.col + BOX.w" y1="24" y2="24" class="col-rule" />
              </g>
              <path v-for="l in view.lines" :key="l.id" :d="l.d"
                    :class="['edge', `edge--${l.kind}`, { 'edge--down': l.status === 'down', 'edge--hl': selected && (l.a === selected || l.b === selected) }]">
                <title>{{ l.a.slice(4) }}{{ l.a_port ? `:${l.a_port}` : "" }} - {{ l.b.slice(l.b.indexOf(":") + 1) }}{{ l.b_port ? `:${l.b_port}` : "" }} ({{ l.status }})</title>
              </path>
              <g v-for="l in view.lines.filter((x) => x.kind === 'cable')" :key="`p-${l.id}`">
                <text v-for="(e, i) in l.ends" :key="i" class="port-t" :x="e.x" :y="e.y" :text-anchor="e.anchor">{{ e.port }}</text>
              </g>
              <g v-for="b in view.boxes" :key="b.id" :transform="`translate(${b.x},${b.y})`" :class="['box', `box--${b.tone}`, { 'box--sel': selected === b.id, 'box--missing': b.status === 'missing' }]"
                 tabindex="0" role="button" :aria-label="`${roleLabel(b)} ${b.name}, ${statusLabel(b)}`" @click="selected = selected === b.id ? null : b.id"
                 @keydown.enter="selected = selected === b.id ? null : b.id">
                <rect :width="BOX.w" :height="BOX.h" rx="4" class="frame" />
                <rect width="4" :height="BOX.h" rx="2" class="strip" />
                <g transform="translate(14,16)" class="glyph"><path :d="glyph(b)" /></g>
                <text x="48" y="17" class="role">{{ roleLabel(b) }}</text>
                <text x="48" y="33" class="name">{{ short(b.name, 20) }}</text>
                <text x="48" y="48" class="sub">{{ short(subtitle(b), 26) }}</text>
                <circle :cx="BOX.w - 12" cy="13" r="4" class="dot" />
                <g v-if="b.new"><rect :x="BOX.w - 52" y="6" width="32" height="14" rx="3" class="badge" /><text :x="BOX.w - 36" y="16.5" class="badge-t">NEW</text></g>
              </g>
            </svg>
          </div>
          <div class="legend">
            <span><i class="lg lg--cable" />Cable (LLDP)</span><span><i class="lg lg--access" />Host on a switch port (ARP)</span>
            <span><i class="lg lg--runs" />Service on a host</span><span><i class="lg lg--down" />Down</span>
            <span><i class="sw sw--ok" />Up</span><span><i class="sw sw--bad" />Down / cut off</span><span><i class="sw sw--action" />Unknown device</span>
            <span class="dim">Click a symbol for details</span>
          </div>
        </UiCard>

        <UiCard v-if="sel" class="side">
          <div class="row row--between"><b>{{ sel.name }}</b><button class="x" aria-label="Close details" @click="selected = null"><UiIcon name="dismiss" :size="16" /></button></div>
          <div class="row mt-2"><UiPill :tone="tone(sel) === 'ok' ? 'ok' : tone(sel)">{{ statusLabel(sel) }}</UiPill><span class="small muted">{{ kindLabel[sel.kind] }}</span></div>
          <dl class="kv mt">
            <template v-if="sel.ip"><dt>Address</dt><dd class="mono">{{ sel.ip }}</dd></template>
            <template v-if="sel.mac"><dt>MAC</dt><dd class="mono">{{ sel.mac }}</dd></template>
            <template v-if="sel.attached"><dt>Plugged into</dt><dd class="mono">{{ sel.attached }}</dd></template>
            <template v-if="sel.role"><dt>Role</dt><dd>{{ sel.role }}</dd></template>
            <template v-if="sel.descr"><dt>System</dt><dd class="small">{{ sel.descr }}</dd></template>
            <template v-if="sel.error"><dt>Error</dt><dd class="bad-text small">{{ sel.error }}</dd></template>
            <dt>First seen</dt><dd>{{ ago(sel.first_seen) }}</dd>
            <dt>Last seen</dt><dd>{{ sel.last_seen ? ago(sel.last_seen) : "-" }}</dd>
          </dl>
          <template v-if="sel.ports?.length">
            <h4 class="h4">Ports</h4>
            <ul class="ports">
              <li v-for="p in sel.ports" :key="p.name"><UiStatusDot :tone="p.up ? 'ok' : 'bad'" :size="7" /><span class="mono">{{ p.name }}</span>
                <span class="small muted">{{ p.mgmt ? "management" : p.ips.join(", ") || p.mac }}</span></li>
            </ul>
          </template>
          <h4 class="h4">Connected to</h4>
          <ul class="ports">
            <li v-for="l in selLinks" :key="l.id"><UiStatusDot :tone="l.status === 'up' ? 'ok' : 'bad'" :size="7" />
              <span>{{ nameOf(l.a === selected ? l.b : l.a) }}</span>
              <span class="small muted mono">{{ l.a === selected ? l.a_port : l.b_port }}</span></li>
          </ul>
          <p v-if="sel.kind === 'host' && !sel.known" class="small mt">Nobody registered this address. If it belongs here, add it under
            <router-link to="/connect">Add a host or service</router-link>; if not, find who plugged into <b class="mono">{{ sel.attached }}</b>.</p>
        </UiCard>
      </div>

      <!-- ---------------- assets ---------------- -->
      <UiCard v-else-if="tab === 'assets'" flush>
        <div class="table-wrap">
          <table class="tbl">
            <thead><tr><th>Name</th><th>Type</th><th>Status</th><th>Address</th><th>MAC</th><th>Where</th><th>First seen</th><th>Last seen</th></tr></thead>
            <tbody>
              <tr v-for="n in nodes" :key="n.id" @click="selected = n.id; tab = 'map'">
                <td><div class="who"><UiAppTile :icon="tileIcon(n)" :size="24" /><b>{{ n.name }}</b><UiPill v-if="n.new" tone="info">new</UiPill></div></td>
                <td>{{ n.kind === "device" ? `${n.role} device` : kindLabel[n.kind] }}</td>
                <td><span class="health"><UiStatusDot :tone="tone(n) === 'action' ? 'warn' : tone(n)" :size="7" />{{ statusLabel(n) }}</span></td>
                <td class="mono">{{ n.ip || "-" }}</td>
                <td class="mono">{{ n.mac || "-" }}</td>
                <td class="mono">{{ n.attached || (n.kind === "device" ? "management" : "-") }}</td>
                <td>{{ ago(n.first_seen) }}</td>
                <td>{{ n.last_seen ? ago(n.last_seen) : "-" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </UiCard>

      <!-- ---------------- changes ---------------- -->
      <UiCard v-else flush>
        <UiEmpty v-if="!topo.events?.length">No changes since discovery started. Links going down, devices that stop answering and new or unknown hosts show up here.</UiEmpty>
        <UiList v-else>
          <UiListRow v-for="e in topo.events" :key="e.id" :title="e.text" :subtitle="`${ago(e.ts)} · ${e.kind.replace(/_/g, ' ')}`">
            <template #accessory><UiPill :tone="sevTone[e.severity] || 'neutral'">{{ e.severity }}</UiPill></template>
          </UiListRow>
        </UiList>
      </UiCard>


    </template>

    <UiCard v-else><UiEmpty>Discovering the network…</UiEmpty></UiCard>
  </div>
</template>

<style scoped>
.tiles { margin-bottom: 16px; }
.mb { margin-bottom: 16px; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-items: start; min-width: 0; }
.layout > * { min-width: 0; }
.canvas-card { min-width: 0; overflow: hidden; }
.layout.with-side { grid-template-columns: minmax(0, 1fr) 320px; }
.canvas { overflow-x: auto; width: 100%; -webkit-overflow-scrolling: touch; }
.canvas svg { display: block; }
.col-label { font-size: 11px; font-weight: 600; fill: var(--c-text-2); letter-spacing: .08em; }
.col-count { fill: var(--c-text-3); font-weight: 500; }
.col-rule { stroke: var(--c-border); stroke-width: 1; }
.edge { fill: none; stroke: var(--c-edge); stroke-width: 1.2; }
.edge--cable { stroke-width: 2.6; stroke: var(--c-text-2); }
.edge--runs { stroke-dasharray: 2 3; }
.edge--down { stroke: var(--c-bad); stroke-dasharray: 6 4; stroke-width: 2.6; }
.edge--hl { stroke: var(--c-primary); }
.edge--down.edge--hl { stroke: var(--c-bad); }
.port-t { font-size: 10px; fill: var(--c-text-3); font-family: var(--font-mono, monospace); }
.box { cursor: pointer; outline: none; }
.frame { fill: var(--c-surface); stroke: var(--c-border); stroke-width: 1; }
.strip { fill: var(--c-ok); }
.box:hover .frame, .box:focus-visible .frame { stroke: var(--c-primary); }
.box--sel .frame { stroke: var(--c-primary); stroke-width: 2; }
.box--bad .frame { fill: var(--c-bad-surface); stroke: var(--c-bad); } .box--bad .strip { fill: var(--c-bad); }
.box--action .frame { fill: var(--c-action-bg); stroke: var(--c-action); } .box--action .strip { fill: var(--c-action); }
.box--neutral .strip { fill: var(--c-neutral); }
.box--missing .frame { stroke-dasharray: 4 3; fill: transparent; }
.glyph path { fill: none; stroke: var(--c-text-2); stroke-width: 1.5; stroke-linecap: round; stroke-linejoin: round; }
.box--bad .glyph path { stroke: var(--c-bad-text); } .box--action .glyph path { stroke: var(--c-action-text); }
.role { font-size: 9.5px; font-weight: 600; letter-spacing: .07em; fill: var(--c-text-3); }
.dot { fill: var(--c-ok); }
.box--bad .dot { fill: var(--c-bad); } .box--action .dot { fill: var(--c-action); } .box--neutral .dot { fill: var(--c-neutral); }
.name { font-size: 13px; font-weight: 600; fill: var(--c-text); }
.sub { font-size: 10.5px; fill: var(--c-text-2); font-family: var(--font-mono, monospace); }
.badge { fill: var(--c-primary); } .badge-t { font-size: 9px; fill: var(--c-on-primary); text-anchor: middle; font-weight: 700; letter-spacing: .05em; }
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--c-separator); font-size: var(--fs-sm); color: var(--c-text-2); }
.legend span { display: inline-flex; align-items: center; gap: 6px; }
.lg { display: inline-block; width: 22px; height: 0; border-top: 2px solid var(--c-edge); }
.lg--cable { border-top: 3px solid var(--c-text-2); } .lg--runs { border-top: 2px dotted var(--c-edge); } .lg--down { border-top: 3px dashed var(--c-bad); }
.sw { display: inline-block; width: 10px; height: 10px; border-radius: 2px; }
.sw--ok { background: var(--c-ok); } .sw--bad { background: var(--c-bad); } .sw--action { background: var(--c-action); }
.side { position: sticky; top: 12px; }
.x { background: none; border: 0; color: var(--c-text-3); cursor: pointer; padding: 4px; border-radius: 6px; }
.kv { display: grid; grid-template-columns: 100px 1fr; gap: 6px 10px; margin: 0; font-size: var(--fs-sm); }
.kv dt { color: var(--c-text-3); } .kv dd { margin: 0; word-break: break-word; }
.h4 { font-size: var(--fs-sm); font-weight: 600; margin: 16px 0 6px; color: var(--c-text-2); }
.ports { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; font-size: var(--fs-sm); }
.ports li { display: flex; align-items: center; gap: 8px; }
.mono { font-family: var(--font-mono, monospace); font-size: 12px; }
.bad-text { color: var(--c-bad-text); }
.table-wrap { overflow-x: auto; }
.tbl { width: 100%; border-collapse: collapse; font-size: var(--fs-md); }
.tbl th { text-align: left; font-size: var(--fs-xs); font-weight: var(--fw-medium); color: var(--c-text-3); padding: 8px 14px; background: var(--c-raised); }
.tbl td { padding: 9px 14px; border-top: 1px solid var(--c-separator); white-space: nowrap; }
.tbl tbody tr { cursor: pointer; }
.tbl tbody tr:hover td { background: var(--c-hover); }
.who { display: flex; align-items: center; gap: 8px; }
.health { display: inline-flex; align-items: center; gap: 6px; }
code { font-family: var(--font-mono, monospace); font-size: 12px; background: var(--c-fill); padding: 1px 5px; border-radius: 4px; }
@media (max-width: 1080px) { .layout.with-side { grid-template-columns: 1fr; } .side { position: static; } }
@media (max-width: 900px) { .grid--4.tiles { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 520px) { .grid--4.tiles { grid-template-columns: minmax(0, 1fr); } }
</style>
