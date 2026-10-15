<script setup>
import { computed, ref } from "vue";
import AutoTraceStatus from "@/components/domain/AutoTraceStatus.vue";
import ServiceRow from "@/components/domain/ServiceRow.vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { bulkBody, connectBody, hostName, installCommand, missing, missingCred, parseTargets, progress } from "@/lib/connect";
import { slug } from "@/lib/format";
import { useRoute } from "vue-router";
import { useCatalogStore } from "@/stores/catalog";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const cat = useCatalogStore();
const route = useRoute();

// ---- connect a server from AIOps: sign in once on this page, AIOps does the rest ----
// address can be pre-filled from the Fleet map ("Monitor this machine" on a discovered VM)
const form = ref({ name: "", address: route.query.address ? String(route.query.address) : "", port: "22", user: "", auth: "password", password: "", key: "", keyFile: "", passphrase: "", ebpf: true });
const suggested = computed(() => hostName("", form.value.address) || "server-name");
const job = ref(null);
const target = ref("");
const ring = computed(() => progress(job.value));
const busy = computed(() => job.value?.state === "running");
async function pickKey(ev) {
  const f = ev.target.files?.[0];
  if (!f) return;
  form.value.key = await f.text();
  form.value.keyFile = f.name;
}
async function connectServer() {
  const why = missing(form.value);
  if (why) return ui.toast(why);
  const body = connectBody(form.value);
  try {
    const { job_id } = await api.connect.ssh(body);
    target.value = body.name;
    Object.assign(form.value, { password: "", key: "", keyFile: "", passphrase: "" });   // not kept in the page either
    job.value = await api.connect.job(job_id);
  } catch (e) {
    ui.toast(e.message);
  }
}
const retry = () => { job.value = null; };

// ---- bulk: connect several machines at once with one shared sign-in (from the Fleet's "Monitor selected") ----
const targets = computed(() => parseTargets(route.query.address, route.query.names));
const bulkMode = computed(() => targets.value.length > 1);
const bulkJobs = ref(null);
const bulkStat = computed(() => {
  const j = bulkJobs.value || [];
  return { total: j.length, done: j.filter((b) => b.job?.state === "done").length,
    failed: j.filter((b) => b.job?.state === "failed").length };
});
const bulkBusy = computed(() => bulkJobs.value?.some((b) => !b.job || b.job.state === "running"));
async function connectBulk() {
  const why = missingCred(form.value);
  if (why) return ui.toast(why);
  try {
    const { jobs } = await api.connect.bulk(bulkBody(form.value, targets.value));
    Object.assign(form.value, { password: "", key: "", keyFile: "", passphrase: "" });
    bulkJobs.value = jobs.map((j) => ({ ...j, job: null }));
  } catch (e) {
    ui.toast(e.message);
  }
}

// ---- what the connected server looks like (also used by "run the command yourself") ----
const own = ref({ name: ui.prefs.computerName || "my-mac", os: "mac" });
const ownName = computed(() => slug(own.value.name) || "my-mac");
const command = computed(() => installCommand({ origin: window.location.origin, name: ownName.value }));
const watching = computed(() => target.value || ownName.value);
const host = ref(null);
const services = ref([]);
usePolling(async () => {
  if (busy.value) job.value = await api.connect.job(job.value.id);
  if (bulkJobs.value) {
    await Promise.all(bulkJobs.value.map(async (b) => {
      if (!b.job || b.job.state === "running") b.job = await api.connect.job(b.job_id);
    }));
  }
  const hosts = await api.hosts.list();
  host.value = hosts.find((h) => h.name === watching.value) || null;
  if (host.value && ["healthy", "problem"].includes(host.value.status)) services.value = (await api.hosts.get(watching.value)).services;
}, 1500);
const connected = computed(() => host.value && ["healthy", "problem"].includes(host.value.status));

// ---- optional step: map the server's own network segment (needs the operator's authorisation) ----
const scanAuthorised = ref(false);
const scanning = ref(false);
const scanDone = ref(false);
async function scanSegment() {
  scanning.value = true;
  try {
    await api.hosts.netscan(target.value);
    scanDone.value = true;
    ui.toast("Scan requested. Machines that reply appear in Your network within a minute.");
  } catch (e) {
    ui.toast(e.message);
  } finally {
    scanning.value = false;
  }
}

const ne = ref({ name: "", address: "" });
async function addNodeExporter() {
  try { await cat.addHost({ ...ne.value }); ui.toast("Server added. First data within 15 s."); } catch (e) { ui.toast(e.message); }
}
</script>
<template>
  <div class="page page--narrow">
    <UiPageHeader :title="bulkMode ? `Monitor ${targets.length} machines` : 'Add a host'" :back="{ to: bulkMode ? '/network' : '/connect', label: bulkMode ? 'Fleet' : 'Add a host or service' }"
                  :subtitle="bulkMode ? 'Sign in once with a credential these machines share. AIOps installs the agent on each and starts watching their services.' : 'Sign in to the server once from here. AIOps installs what it needs, then finds and watches every service on it.'" />

    <!-- bulk: one shared sign-in for many machines -->
    <section v-if="bulkMode && !bulkJobs" class="card">
      <label class="lbl lbl--top">Machines to monitor ({{ targets.length }})</label>
      <div class="targets">
        <span v-for="t in targets" :key="t.address" class="target">{{ t.name || t.address }}</span>
      </div>
      <div class="grid2 mt-2">
        <UiField v-model="form.user" label="User (same on every machine)" placeholder="ubuntu" mono />
        <UiField v-model="form.port" label="SSH port" placeholder="22" mono />
      </div>
      <label class="lbl">Sign in with</label>
      <UiSegmented v-model="form.auth" :options="[{ value: 'password', label: 'Password' }, { value: 'key', label: 'SSH key file' }]" label="Sign in with" />
      <UiField v-if="form.auth === 'password'" v-model="form.password" type="password" label="Password" class="mt" @enter="connectBulk" />
      <template v-else>
        <label class="file mt"><input type="file" @change="pickKey" /><span>{{ form.keyFile || "Choose the key these machines accept" }}</span></label>
        <UiField v-model="form.passphrase" type="password" label="Key passphrase" hint="(only if it has one)" />
      </template>
      <div class="row mt-2"><UiSwitch v-model="form.ebpf" label="Trace their services automatically" /><span>Logs, metrics and traces for every service on each machine</span></div>
      <UiButton class="mt connect" @click="connectBulk">Connect {{ targets.length }} machines</UiButton>
      <p class="small muted mt-2">One credential, used once per machine to install the agent, then forgotten. Machines that refuse it are reported on their own — the rest still connect.</p>
    </section>

    <section v-else-if="bulkMode" class="card">
      <div class="progress">
        <UiProgressRing :value="bulkStat.total ? (bulkStat.done + bulkStat.failed) / bulkStat.total : 0" :state="bulkBusy ? 'running' : 'done'" />
        <div>
          <b class="now">{{ bulkBusy ? `Connecting ${bulkStat.total} machines…` : `${bulkStat.done} of ${bulkStat.total} connected` }}</b>
          <div class="muted small">{{ bulkStat.failed ? `${bulkStat.failed} could not be reached` : "One shared sign-in, one agent per machine" }}</div>
        </div>
      </div>
      <ul class="hostlist">
        <li v-for="b in bulkJobs" :key="b.job_id">
          <UiProgressRing :value="progress(b.job).value" :state="progress(b.job).state" :size="26" />
          <router-link :to="`/computers/${b.name}`" class="hl-name">{{ b.name }}</router-link>
          <span class="muted small">{{ b.job?.state === "failed" ? b.job.error : b.job?.state === "done" ? "connected" : progress(b.job).label || "starting…" }}</span>
        </li>
      </ul>
      <div class="row mt"><UiButton variant="tint" to="/network">Open the Fleet map</UiButton></div>
    </section>

    <section v-if="!bulkMode && (!job || job.state === 'failed')" class="card">
      <div class="grid2">
        <UiField v-model="form.address" label="Server address" placeholder="34.2.129.3" mono />
        <UiField v-model="form.user" label="User" placeholder="ubuntu" mono />
      </div>
      <label class="lbl">Sign in with</label>
      <UiSegmented v-model="form.auth" :options="[{ value: 'password', label: 'Password' }, { value: 'key', label: 'SSH key file' }]" label="Sign in with" />
      <UiField v-if="form.auth === 'password'" v-model="form.password" type="password" label="Password" class="mt" @enter="connectServer" />
      <template v-else>
        <label class="file mt"><input type="file" @change="pickKey" /><span>{{ form.keyFile || "Choose the key file you use for this server" }}</span></label>
        <UiField v-model="form.passphrase" type="password" label="Key passphrase" hint="(only if it has one)" />
      </template>
      <UiDisclosure :card="false" title="More options" class="mt-2">
        <div class="grid2">
          <UiField v-model="form.name" label="Name in AIOps" :placeholder="suggested" />
          <UiField v-model="form.port" label="SSH port" placeholder="22" mono />
        </div>
        <div class="row mt-2"><UiSwitch v-model="form.ebpf" label="Trace its services automatically" /><span>Logs, metrics and traces for every service (collector capped at 256 MB, eBPF tracer at 384 MB)</span></div>
      </UiDisclosure>
      <p v-if="job?.state === 'failed'" class="small bad mt-2">{{ job.error }}</p>
      <UiButton class="mt connect" @click="connectServer">{{ job?.state === "failed" ? "Try again" : "Connect" }}</UiButton>
      <p class="small muted mt-2">Used once to install the agent, then forgotten. AIOps keeps the connection open with its own key, which can only open two ports on the server's loopback - it cannot run anything there.</p>
    </section>

    <section v-else-if="!bulkMode" class="card">
      <div class="progress">
        <UiProgressRing :value="ring.value" :state="ring.state" />
        <div>
          <b class="now">{{ ring.state === "done" ? `${target} is connected` : `${ring.label}…` }}</b>
          <div class="muted small">{{ ring.state === "done" ? "Server and services are being watched" : `Connecting ${target}` }}</div>
        </div>
      </div>
      <ol class="checklist">
        <li v-for="s in job.steps" :key="s.key" :class="s.state">
          <UiIcon v-if="s.state === 'done'" name="checkmark_circle" filled :size="18" />
          <UiIcon v-else-if="s.state === 'failed'" name="dismiss" :size="18" />
          <span v-else class="dot" />
          {{ s.label }}
        </li>
      </ol>
      <UiDisclosure v-if="job.log.length" :card="false" title="What AIOps did on the server" class="mt-2">
        <UiCodeBlock :code="job.log.slice(-16).join('\n')" />
      </UiDisclosure>
      <template v-if="ring.state === 'done' && connected">
        <div class="stats mt">CPU {{ Math.round(host.cpu) }}% · Memory {{ Math.round(host.mem) }}% · Disk {{ Math.round(host.disk) }}%</div>
        <div class="section-label">Services found on {{ target }} ({{ services.length }})</div>
        <UiList><ServiceRow v-for="s in services" :key="s.service" :service="s" /></UiList>
        <AutoTraceStatus class="mt" :host="host" :services="services" />
        <div class="section-label">Map its network <span class="muted">(optional)</span></div>
        <p class="small muted">AIOps already lists the machines this server hears on its network. To also find machines that stay quiet, it can send one round of ARP requests across the server's own segment — it never touches another network or any service port. Only on a network you are authorised to scan; on a shared network, ask the owner first.</p>
        <div class="row mt-2"><UiSwitch v-model="scanAuthorised" label="I am authorised to scan this server's network" /><span>I am authorised to scan this server's network</span></div>
        <div class="row mt"><UiButton :disabled="!scanAuthorised || scanning || scanDone" @click="scanSegment">{{ scanDone ? "Scan requested" : scanning ? "Requesting…" : "Scan its segment once" }}</UiButton><UiButton variant="tint" :to="`/computers/${target}`">View {{ target }}</UiButton><UiButton variant="tint" to="/network">Fleet map</UiButton></div>
      </template>
    </section>

    <UiDisclosure v-if="!bulkMode" class="mt" title="A laptop, or a machine you would rather set up yourself">
      <div class="grid2">
        <UiField v-model="own.name" label="Computer name" />
        <div><label class="lbl lbl--top">System</label>
          <UiSegmented v-model="own.os" :options="[{ value: 'mac', label: 'macOS', logo: 'apple' }, { value: 'linux', label: 'Linux', logo: 'linux' }]" label="System" /></div>
      </div>
      <p class="small muted mt-2">Paste this in Terminal on that machine. It must reach this server (KMUTT network or VPN).</p>
      <UiCodeBlock :code="command" />
      <p v-if="!target && host" class="small mt-2">{{ connected ? `${ownName} is connected.` : `${ownName} is registered, waiting for its first measurements…` }}</p>
    </UiDisclosure>
    <UiDisclosure v-if="!bulkMode" class="mt" title="A server that already runs node_exporter">
      <p class="small muted">AIOps collects from it on port 9100, so it must be reachable from this server.</p>
      <UiField v-model="ne.name" label="Name" placeholder="db-01" />
      <UiField v-model="ne.address" label="Address" placeholder="10.4.82.30:9100" mono />
      <UiButton variant="tint" class="mt" @click="addNodeExporter">Add server</UiButton>
    </UiDisclosure>
  </div>
</template>
<style scoped>
.card { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 22px 24px; }
.grid2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.lbl { display: block; font-size: var(--fs-sm); color: var(--c-text-2); margin: 12px 0 6px; font-weight: 500; }
.lbl--top { margin-top: 0; }
.file { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px dashed var(--c-text-3); border-radius: 10px; cursor: pointer; margin-bottom: 10px; }
.file input { max-width: 110px; }
.connect { min-width: 160px; }
.progress { display: flex; align-items: center; gap: 20px; }
.now { font-size: var(--fs-lg); display: block; margin-bottom: 2px; }
.checklist { list-style: none; padding: 0; margin: 18px 0 0; display: grid; gap: 8px; }
.checklist li { display: flex; align-items: center; gap: 10px; color: var(--c-text-3); }
.checklist li.done { color: var(--c-ok-text); }
.checklist li.running { color: var(--c-text); font-weight: var(--fw-semibold); }
.checklist li.failed { color: var(--c-bad-text); }
.dot { width: 18px; height: 18px; border-radius: 50%; border: 2px solid currentColor; flex: none; }
.checklist li.running .dot { border-color: var(--c-primary); background: radial-gradient(var(--c-primary) 35%, transparent 40%); }
.stats { font-weight: var(--fw-semibold); }
.targets { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
.target { font-size: var(--fs-sm); background: var(--c-fill); border: 1px solid var(--c-border); border-radius: var(--radius-sm); padding: 3px 8px; font-family: var(--font-mono, monospace); }
.hostlist { list-style: none; padding: 0; margin: 18px 0 0; display: grid; gap: 10px; }
.hostlist li { display: grid; grid-template-columns: 26px minmax(0, 1fr) auto; align-items: center; gap: 10px; }
.hl-name { font-weight: var(--fw-medium); overflow-wrap: anywhere; }
@media (max-width: 640px) { .grid2 { grid-template-columns: 1fr; } .progress { gap: 14px; } }
</style>
