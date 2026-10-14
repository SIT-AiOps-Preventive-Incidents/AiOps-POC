<script setup>
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { ago } from "@/lib/format";
import { BOX, LAYERS, layout, statusLabel, tone } from "@/lib/netlayout";
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

      <UiSegmented v-model="tab" :options="tabs" label="Network view" class="tabs" />

      <!-- ---------------- topology ---------------- -->
      <div v-if="tab === 'map'" :class="['layout', { 'with-side': sel }]">
        <UiCard class="canvas-card">
          <div class="canvas" role="img" :aria-label="`Network topology with ${nodes.length} items`">
            <svg :viewBox="`-4 0 ${view.width + 8} ${view.height}`" :width="view.width + 8" :height="view.height">
              <text v-for="(l, i) in LAYERS" :key="l" :x="i * BOX.col" y="16" class="col-label">{{ l }}</text>
              <path v-for="l in view.lines" :key="l.id" :d="l.d"
                    :class="['edge', `edge--${l.kind}`, { 'edge--down': l.status === 'down', 'edge--hl': selected && (l.a === selected || l.b === selected) }]">
                <title>{{ l.a.slice(4) }}{{ l.a_port ? `:${l.a_port}` : "" }} - {{ l.b.slice(l.b.indexOf(":") + 1) }}{{ l.b_port ? `:${l.b_port}` : "" }} ({{ l.status }})</title>
              </path>
              <g v-for="b in view.boxes" :key="b.id" :transform="`translate(${b.x},${b.y})`" :class="['box', `box--${b.tone}`, { 'box--sel': selected === b.id, 'box--missing': b.status === 'missing' }]"
                 tabindex="0" role="button" :aria-label="`${b.name}, ${statusLabel(b)}`" @click="selected = selected === b.id ? null : b.id"
                 @keydown.enter="selected = selected === b.id ? null : b.id">
                <rect :width="BOX.w" :height="BOX.h" rx="7" />
                <circle cx="14" cy="18" r="4.5" class="dot" />
                <text x="26" y="22" class="name">{{ short(b.name) }}</text>
                <text x="14" y="40" class="sub">{{ short(subtitle(b), 27) }}</text>
                <g v-if="b.new"><rect :x="BOX.w - 38" y="8" width="30" height="16" rx="8" class="badge" /><text :x="BOX.w - 23" y="20" class="badge-t">new</text></g>
              </g>
            </svg>
          </div>
          <p class="small dim legend">Thick lines are cables found over LLDP; thin lines are hosts a switch sees on a port (ARP); dotted lines are the services on a host.
            Red is down or cut off from the core, orange is a device nobody registered. Click a box for details.</p>
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

      <p class="small dim mt-2">Polled: {{ (topo.sources || []).join(", ") }} · last scan {{ ago(topo.ts) }}</p>
    </template>

    <UiCard v-else><UiEmpty>Discovering the network…</UiEmpty></UiCard>
  </div>
</template>

<style scoped>
.tiles { margin-bottom: 16px; }
.tabs { margin-bottom: 14px; }
.mb { margin-bottom: 16px; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-items: start; min-width: 0; }
.layout > * { min-width: 0; }
.canvas-card { min-width: 0; overflow: hidden; }
.layout.with-side { grid-template-columns: minmax(0, 1fr) 320px; }
.canvas { overflow-x: auto; width: 100%; -webkit-overflow-scrolling: touch; }
.canvas svg { display: block; }
.legend { margin: 10px 0 0; }
.col-label { font-size: 11px; font-weight: 600; fill: var(--c-text-3); text-transform: uppercase; letter-spacing: .06em; }
.edge { fill: none; stroke: var(--c-edge); stroke-width: 1.4; }
.edge--cable { stroke-width: 3; stroke: var(--c-text-3); }
.edge--runs { stroke-dasharray: 2 4; }
.edge--down { stroke: var(--c-bad); stroke-dasharray: 7 5; }
.edge--hl { stroke: var(--c-primary); }
.edge--down.edge--hl { stroke: var(--c-bad); }
.box { cursor: pointer; outline: none; }
.box rect:first-child { fill: var(--c-surface); stroke: var(--c-border); stroke-width: 1; }
.box:hover rect:first-child, .box:focus-visible rect:first-child { stroke: var(--c-primary); }
.box--sel rect:first-child { stroke: var(--c-primary); stroke-width: 2; }
.box--bad rect:first-child { fill: var(--c-bad-surface); stroke: var(--c-bad); }
.box--action rect:first-child { fill: var(--c-action-bg); stroke: var(--c-action); }
.box--missing rect:first-child { stroke-dasharray: 4 3; fill: transparent; }
.dot { fill: var(--c-ok); }
.box--bad .dot { fill: var(--c-bad); } .box--action .dot { fill: var(--c-action); } .box--neutral .dot { fill: var(--c-neutral); }
.name { font-size: 13px; font-weight: 600; fill: var(--c-text); }
.sub { font-size: 11px; fill: var(--c-text-2); font-family: var(--font-mono, monospace); }
.badge { fill: var(--c-info-bg); } .badge-t { font-size: 10px; fill: var(--c-info-text); text-anchor: middle; font-weight: 600; }
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
