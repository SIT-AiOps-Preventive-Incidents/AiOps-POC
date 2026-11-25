<script setup>
/**
 * Cloud accounts - the machines you rent, not the ones you can hear on a LAN. Connect an account with a read-only
 * credential; RadarOps lists every VM in it, re-reads it every few minutes, and says for each one what the cloud
 * and our agent see together (running but silent, stopped in the console, not monitored yet...).
 */
import { computed, ref } from "vue";
import { usePageFacts } from "@/composables/usePageFacts";
import { useRoute, useRouter } from "vue-router";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { ago } from "@/lib/format";
import { bodyFor, fieldsFor, missing, verdictTone } from "@/lib/cloudform";
import { useUiStore } from "@/stores/ui";

const route = useRoute();
const router = useRouter();
const ui = useUiStore();
const providers = ref([]);
const accounts = ref(null);
const instances = ref([]);
const events = ref([]);
const error = ref("");
async function load() {
  try {
    [accounts.value, instances.value, events.value] = await Promise.all([api.cloud.accounts(), api.cloud.instances(), api.cloud.events()]);
    error.value = "";
  } catch (e) { error.value = e.message; }
}
usePolling(load, 20000);
api.cloud.providers().then((p) => (providers.value = p));

// ---- connect form ----
const adding = ref(route.query.add === "1");
const pid = ref("proxmox");
const name = ref("");
const values = ref({ verify_tls: true });
const busy = ref(false);
const formError = ref("");
const spec = computed(() => providers.value.find((p) => p.id === pid.value));
const fields = computed(() => (spec.value ? fieldsFor(spec.value) : []));
const todo = computed(() => (spec.value ? missing(spec.value, name.value, values.value) : ["provider"]));
function pick(id) { pid.value = id; values.value = { verify_tls: true }; formError.value = ""; }
async function connect() {
  busy.value = true; formError.value = "";
  try {
    const r = await api.cloud.add(bodyFor(spec.value, name.value, values.value));
    ui.toast(`Connected ${r.account.name}: ${r.sync.instances} machine${r.sync.instances === 1 ? "" : "s"} found`);
    adding.value = false; name.value = ""; values.value = { verify_tls: true };
    router.replace({ query: {} });
    await load();
  } catch (e) { formError.value = e.message; } finally { busy.value = false; }
}
async function sync(a) {
  try { const r = await api.cloud.sync(a.id); ui.toast(`${a.name}: ${r.instances} machines · ${r.added} new · ${r.removed} gone · ${r.changed} changed`); await load(); }
  catch (e) { ui.toast(e.message); }
}
// disconnect is two clicks: the first arms the button, the second deletes (nothing changes in the cloud itself)
const armed = ref(null);
async function remove(a) {
  if (armed.value !== a.id) { armed.value = a.id; setTimeout(() => { if (armed.value === a.id) armed.value = null; }, 4000); return; }
  armed.value = null;
  await api.cloud.remove(a.id); ui.toast(`Disconnected ${a.name}`); await load();
}

// ---- machines ----
const filter = ref("all");
const FILTERS = [{ value: "all", label: "All" }, { value: "attention", label: "Needs attention" }, { value: "unmonitored", label: "Not monitored" }];
const shown = computed(() => instances.value.filter((i) => filter.value === "all"
  || (filter.value === "attention" && ["agent_silent", "error", "stopped_in_cloud"].includes(i.verdict.code))
  || (filter.value === "unmonitored" && i.verdict.code === "not_monitored")));
const counts = computed(() => ({
  total: instances.value.length, running: instances.value.filter((i) => i.state === "running").length,
  monitored: instances.value.filter((i) => i.aiops_host).length,
  attention: instances.value.filter((i) => ["agent_silent", "error", "stopped_in_cloud"].includes(i.verdict.code)).length,
}));
const STATE_TONE = { running: "ok", stopped: "neutral", starting: "info", stopping: "info", error: "bad", unknown: "neutral" };
const monitor = (i) => router.push({ path: "/connect/computer", query: { address: (i.public_ips[0] || i.private_ips[0]), names: i.name } });
const providerLabel = (id) => providers.value.find((p) => p.id === id)?.label || id;
usePageFacts(() => ({
  cloud_accounts: accounts.value?.length, known_machines: accounts.value ? counts.value.total : undefined,
  monitored_hosts: accounts.value ? counts.value.monitored : undefined,
  hosts_with_issues: accounts.value ? counts.value.attention : undefined,
  ...(busy.value ? { connecting: 1 } : {}), ...(error.value && accounts.value ? { stale_data: 1 } : {}),
}));
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader eyebrow="Fleet" title="Cloud accounts"
                  subtitle="Every VM in the clouds you rent, read with a read-only credential and re-read every few minutes. Proxmox (GIST Starships Cloud), OpenStack, VMware Cloud Director, CloudStack, AWS, Azure and Google Cloud.">
      <UiButton v-can="'fleet.cloud'" v-if="!adding" icon="add" @click="adding = true">Connect a cloud</UiButton>
    </UiPageHeader>

    <!-- connect -->
    <section v-if="adding" class="card connect">
      <div class="connect__head">
        <div><h3>Connect a cloud account</h3><p class="sub">The credential is tried first. Nothing is saved unless it can list your machines.</p></div>
        <UiButton variant="ghost" icon="dismiss" aria-label="Close" @click="adding = false; router.replace({ query: {} })" />
      </div>
      <div class="provs" role="radiogroup" aria-label="Cloud provider">
        <button v-for="p in providers" :key="p.id" type="button" role="radio" :aria-checked="pid === p.id" :class="['prov', { on: pid === p.id }]" @click="pick(p.id)">
          <UiGlyph name="cloud" :size="20" /><span>{{ p.label }}</span>
        </button>
      </div>
      <div v-if="spec" class="connect__body">
        <div class="form">
          <UiField v-model="name" label="Name" placeholder="e.g. GIST Starships · production" />
          <template v-for="f in fields" :key="f.key">
            <label v-if="f.type === 'switch'" class="switch-row"><span>{{ f.label }}</span>
              <UiSwitch :model-value="values[f.key] !== false" :label="f.label" @update:model-value="(v) => (values = { ...values, [f.key]: v })" /></label>
            <UiField v-else v-model="values[f.key]" :label="f.label" :hint="f.required ? '' : 'optional'" :placeholder="f.placeholder"
                     :type="f.type === 'password' ? 'password' : 'text'" :multiline="f.type === 'textarea'" :mono="f.secret" />
          </template>
          <p v-if="formError" class="err">{{ formError }}</p>
          <div class="form__go">
            <UiButton :loading="busy" :disabled="todo.length > 0" chevron @click="connect">Test and connect</UiButton>
            <span v-if="todo.length" class="muted small">Still needed: {{ todo.map((k) => fields.find((f) => f.key === k)?.label || k).join(", ") }}</span>
          </div>
        </div>
        <aside class="least">
          <p class="least__k">Give SIT-AIOPS only this</p>
          <p class="least__v">{{ spec.role }}.</p>
          <p class="least__k">What it reads</p>
          <p class="least__v">The list of VMs, their power state, addresses, network and size. It never starts, stops or changes anything.</p>
          <p class="least__k">Where the credential goes</p>
          <p class="least__v">Sealed with a key that never leaves this server, and never shown again. Disconnecting deletes it.</p>
          <p v-if="pid === 'proxmox'" class="least__note">GIST Starships Cloud runs on Proxmox VE. Ask GIST for an API token with the PVEAuditor role on your resource pool, and install the QEMU guest agent in your VMs so their addresses show up.</p>
        </aside>
      </div>
    </section>

    <!-- accounts -->
    <div v-if="accounts && accounts.length" class="accounts">
      <section v-for="a in accounts" :key="a.id" class="card acc">
        <div class="acc__top">
          <div>
            <h3>{{ a.name }}</h3>
            <p class="sub">{{ providerLabel(a.provider) }}</p>
            <p class="state"><UiStatusDot :tone="a.status === 'ok' ? 'ok' : a.status === 'error' ? 'bad' : 'neutral'" :size="9" />
              {{ a.status === "ok" ? "Connected" : a.status === "error" ? "Read failed" : "New" }}</p>
          </div>
          <UiGauge :ratio="a.instance_count ? 1 : 0" :value="a.instance_count" unit="machines" :tone="a.status === 'error' ? 'bad' : 'info'" :size="96" />
        </div>
        <p v-if="a.last_error" class="err small">{{ a.last_error }}</p>
        <div class="acc__foot">
          <span class="muted small">{{ a.last_sync_at ? `Read ${ago(a.last_sync_at)}` : "Not read yet" }}</span>
          <div class="row"><UiButton v-can="'fleet.cloud'" size="sm" variant="tint" icon="arrow_sync" @click="sync(a)">Read now</UiButton>
            <UiButton v-can="'fleet.cloud'" size="sm" :variant="armed === a.id ? 'danger' : 'ghost'" @click="remove(a)">{{ armed === a.id ? "Click to confirm" : "Disconnect" }}</UiButton></div>
        </div>
      </section>
    </div>
    <section v-else-if="accounts && !adding" class="card empty">
      <UiGlyph name="cloud" :size="40" />
      <div><b>No cloud account yet</b><p class="muted">Connect one to see every VM you rent next to the machines on your own network.</p></div>
      <UiButton v-can="'fleet.cloud'" icon="add" @click="adding = true">Connect a cloud</UiButton>
    </section>
    <p v-if="error" class="err">{{ error }}</p>

    <!-- machines -->
    <section v-if="instances.length" class="card">
      <div class="m-head">
        <div><h3>Machines</h3><p class="sub">{{ counts.total }} in your clouds · {{ counts.running }} running · {{ counts.monitored }} with our agent · {{ counts.attention }} need attention</p></div>
        <UiSegmented v-model="filter" :options="FILTERS" label="Show" />
      </div>
      <div class="table">
        <div class="tr th"><span>Machine</span><span>Cloud</span><span>Address</span><span>State</span><span>What it means</span><span /></div>
        <div v-for="i in shown" :key="`${i.account_id}:${i.instance_id}`" class="tr">
          <span class="nm"><b>{{ i.name }}</b><small>{{ i.size || i.instance_id }}<template v-if="i.zone"> · {{ i.zone }}</template></small></span>
          <span class="muted">{{ i.account }}</span>
          <span class="mono small">{{ i.private_ips[0] || "–" }}<small v-if="i.public_ips[0]">{{ i.public_ips[0] }}</small></span>
          <span class="st"><UiStatusDot :tone="STATE_TONE[i.state] || 'neutral'" :size="8" />{{ i.state }}</span>
          <span :class="['vd', `t-${verdictTone(i.verdict.code)}`]">{{ i.verdict.text }}</span>
          <span class="act">
            <UiButton v-if="i.aiops_host" size="sm" variant="tint" :to="`/computers/${i.aiops_host}`" chevron>Host</UiButton>
            <UiButton v-can="'fleet.connect'" v-else-if="i.state === 'running' && (i.private_ips[0] || i.public_ips[0])" size="sm" icon="add" @click="monitor(i)">Monitor</UiButton>
          </span>
        </div>
      </div>
    </section>

    <section v-if="events.length" class="card">
      <h3>What changed</h3>
      <ul class="events">
        <li v-for="e in events.slice(0, 12)" :key="e.id"><UiStatusDot :tone="e.kind === 'removed' ? 'bad' : e.kind === 'added' ? 'ok' : 'info'" :size="8" />
          <b>{{ e.name }}</b><span class="muted">{{ e.kind === "added" ? "appeared" : e.kind === "removed" ? "was deleted" : e.detail }}</span>
          <span class="dim small">{{ e.account }} · {{ ago(e.ts) }}</span></li>
      </ul>
    </section>
  </div>
</template>
<style scoped>
.card { background: var(--surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-card); padding: 22px 24px; margin-bottom: 16px; }
.card h3 { font-size: 20px; font-weight: var(--fw-semibold); letter-spacing: -0.02em; }
.sub { font-size: var(--fs-sm); color: var(--c-text-3); margin-top: 4px; }
.state { display: flex; align-items: center; gap: 8px; margin-top: 12px; font-weight: var(--fw-semibold); }
.err { color: var(--c-bad-text); margin-top: 10px; }
.connect__head { display: flex; justify-content: space-between; gap: 12px; }
.provs { display: flex; flex-wrap: wrap; gap: 8px; margin: 18px 0 6px; }
.prov { display: inline-flex; align-items: center; gap: 8px; height: 40px; padding: 0 14px; border-radius: 12px; border: 1px solid var(--c-border);
  background: var(--c-fill); color: var(--c-text-2); cursor: pointer; font-weight: var(--fw-medium); }
.prov:hover { color: var(--c-text); }
.prov.on { background: var(--c-primary-tint); border-color: color-mix(in srgb, var(--c-primary) 50%, transparent); color: var(--c-text); }
.prov.on .ui-icon { color: var(--c-primary); }
.connect__body { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 28px; align-items: start; }
.switch-row { display: flex; justify-content: space-between; align-items: center; margin-top: 16px; font-size: var(--fs-sm); color: var(--c-text-2); }
.form__go { display: flex; align-items: center; gap: 14px; margin-top: 20px; flex-wrap: wrap; }
.least { background: var(--c-fill); border-radius: 14px; padding: 18px; margin-top: 14px; }
.least__k { font-size: 10.5px; font-weight: var(--fw-semibold); text-transform: uppercase; letter-spacing: 0.09em; color: var(--c-text-3); margin-top: 14px; }
.least__k:first-child { margin-top: 0; }
.least__v { margin-top: 4px; font-size: var(--fs-sm); }
.least__note { margin-top: 16px; padding-top: 14px; border-top: 1px solid var(--c-border); font-size: var(--fs-sm); color: var(--c-text-2); }
.accounts { display: grid; grid-template-columns: repeat(auto-fill, minmax(330px, 1fr)); gap: 16px; margin-bottom: 0; }
.acc__top { display: flex; justify-content: space-between; gap: 12px; }
.acc__foot { display: flex; justify-content: space-between; align-items: center; gap: 8px; margin-top: 18px; padding-top: 14px; border-top: 1px solid var(--c-separator); flex-wrap: wrap; }
.row { display: flex; gap: 6px; }
.empty { display: flex; align-items: center; gap: 18px; } .empty > div { flex: 1; } .empty .ui-icon { color: var(--c-text-3); }
.m-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; flex-wrap: wrap; margin-bottom: 14px; }
.table { display: flex; flex-direction: column; }
.tr { display: grid; grid-template-columns: minmax(170px, 1.4fr) minmax(110px, 1fr) minmax(120px, 1fr) 110px minmax(200px, 2fr) 110px;
  gap: 14px; align-items: center; padding: 13px 4px; border-top: 1px solid var(--c-separator); }
.th { border-top: 0; font-size: 10.5px; font-weight: var(--fw-semibold); text-transform: uppercase; letter-spacing: 0.09em; color: var(--c-text-3); padding-top: 0; }
.nm { display: flex; flex-direction: column; min-width: 0; } .nm small, .mono small { display: block; font-size: var(--fs-xs); color: var(--c-text-3); }
.st { display: inline-flex; align-items: center; gap: 7px; text-transform: capitalize; }
.vd { font-size: var(--fs-sm); } .vd.t-bad { color: var(--c-bad-text); } .vd.t-warn { color: var(--c-warn-text); } .vd.t-ok { color: var(--c-ok-text); }
.vd.t-neutral, .vd.t-info { color: var(--c-text-2); }
.act { justify-self: end; }
.events { list-style: none; padding: 0; margin: 12px 0 0; }
.events li { display: flex; align-items: center; gap: 10px; padding: 9px 0; border-top: 1px solid var(--c-separator); flex-wrap: wrap; }
.events li:first-child { border-top: 0; } .events .dim { margin-left: auto; }
@media (max-width: 1080px) { .connect__body { grid-template-columns: 1fr; } .tr { grid-template-columns: 1fr 1fr; } .th { display: none; } .act { justify-self: start; } }
</style>
