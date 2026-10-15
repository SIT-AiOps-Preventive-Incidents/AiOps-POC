<script setup>
import { computed, ref, watch } from "vue";
import AutoTraceStatus from "@/components/domain/AutoTraceStatus.vue";
import ServiceRow from "@/components/domain/ServiceRow.vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { connectBody, installCommand, missing } from "@/lib/connect";
import { slug } from "@/lib/format";
import { useCatalogStore } from "@/stores/catalog";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const cat = useCatalogStore();
const name = ref(ui.prefs.computerName || "my-mac");
const os = ref("mac");
const origin = window.location.origin;
const clean = computed(() => slug(name.value) || "my-mac");
const command = computed(() => installCommand({ origin, name: clean.value }));
watch(clean, (v) => ui.setPref("computerName", v));

// Linux servers: AIOps signs in once and does the rest, or the user runs the command
const how = ref("platform");
const fromAiops = computed(() => os.value === "linux" && how.value === "platform");
const form = ref({ address: "", port: "22", user: "", auth: "key", password: "", key: "", keyFile: "", passphrase: "", ebpf: true });
const job = ref(null);
const running = computed(() => job.value?.state === "running");
async function pickKey(ev) {
  const f = ev.target.files?.[0];
  if (!f) return;
  form.value.key = await f.text();
  form.value.keyFile = f.name;
}
async function connectServer() {
  const why = missing(form.value);
  if (why) return ui.toast(why);
  try {
    const { job_id } = await api.connect.ssh(connectBody(clean.value, form.value));
    form.value.password = ""; form.value.key = ""; form.value.passphrase = "";   // not kept in the page either
    job.value = await api.connect.job(job_id);
  } catch (e) {
    ui.toast(e.message);
  }
}
usePolling(async () => {
  if (running.value) job.value = await api.connect.job(job.value.id);
}, 1500);
const STEP_TONE = { done: "ok", running: "info", failed: "bad", pending: "neutral" };
const STEP_TEXT = { done: "Done", running: "Working", failed: "Failed", pending: "Waiting" };

// live status: not seen -> registered -> metrics -> services discovered
const host = ref(null);
const services = ref([]);
usePolling(async () => {
  const hosts = await api.hosts.list();
  host.value = hosts.find((h) => h.name === clean.value) || null;
  if (host.value && ["healthy", "problem"].includes(host.value.status)) services.value = (await api.hosts.get(clean.value)).services;
}, 3000);
const connected = computed(() => host.value && ["healthy", "problem"].includes(host.value.status));

const ne = ref({ name: "", address: "" });
async function addNodeExporter() {
  try { await cat.addHost({ ...ne.value }); ui.toast("Server added. First data within 15 s."); } catch (e) { ui.toast(e.message); }
}
</script>
<template>
  <div class="page page--narrow">
    <UiPageHeader title="Add a host" :back="{ to: '/connect', label: 'Add a host or service' }" />
    <ol class="steps">
      <li class="step done"><span class="n">1</span><div class="body"><h2>Name it</h2>
        <UiField v-model="name" label="Computer name" />
        <label class="lbl">System</label>
        <UiSegmented v-model="os" :options="[{ value: 'mac', label: 'macOS', logo: 'apple' }, { value: 'linux', label: 'Linux', logo: 'linux' }]" label="System" />
        <template v-if="os === 'linux'">
          <label class="lbl">How to connect it</label>
          <UiSegmented v-model="how" :options="[{ value: 'platform', label: 'From AIOps - no command' }, { value: 'command', label: 'Run a command myself' }]" label="How" />
        </template></div></li>
      <li v-if="fromAiops" :class="['step', { done: job?.state === 'done' }]"><span class="n">2</span><div class="body"><h2>Sign in to the server once</h2>
        <template v-if="!job || job.state === 'failed'">
          <div class="grid2">
            <UiField v-model="form.address" label="Server address" placeholder="34.2.129.3" mono />
            <UiField v-model="form.user" label="User" placeholder="ubuntu" mono />
          </div>
          <label class="lbl">Sign in with</label>
          <UiSegmented v-model="form.auth" :options="[{ value: 'key', label: 'SSH key file' }, { value: 'password', label: 'Password' }]" label="Sign in with" />
          <UiField v-if="form.auth === 'password'" v-model="form.password" type="password" label="Password" class="mt" @enter="connectServer" />
          <template v-else>
            <label class="file mt"><input type="file" @change="pickKey" /><span>{{ form.keyFile || "Choose the key file you use for this server" }}</span></label>
            <UiField v-model="form.passphrase" type="password" label="Key passphrase" hint="(only if it has one)" />
          </template>
          <div class="row mt"><UiSwitch v-model="form.ebpf" label="Trace its services automatically" /><span>Trace its services automatically (eBPF, capped at 200 MB)</span></div>
          <UiButton class="mt" @click="connectServer">Connect</UiButton>
          <p class="small muted mt-2">Used once to install the agent, then forgotten. AIOps keeps the data channel open with its own key, which can only open two ports on the server's loopback - no shell.</p>
          <p v-if="job?.state === 'failed'" class="small bad mt-2">{{ job.error }}</p>
        </template>
        <template v-if="job">
          <UiList plain class="mt">
            <UiListRow v-for="s in job.steps" :key="s.key" :title="s.label">
              <template #accessory><UiSpinner v-if="s.state === 'running'" :size="16" /><UiPill v-else :tone="STEP_TONE[s.state]">{{ STEP_TEXT[s.state] }}</UiPill></template>
            </UiListRow>
          </UiList>
          <UiDisclosure v-if="job.log.length" :card="false" title="What AIOps did on the server" class="mt-2">
            <UiCodeBlock :code="job.log.slice(-14).join('\n')" />
          </UiDisclosure>
        </template></div></li>
      <li v-else class="step done"><span class="n">2</span><div class="body"><h2>Paste this in Terminal {{ os === "mac" ? "on the Mac" : "on the server" }}</h2>
        <UiCodeBlock :code="command" />
        <p class="small muted mt-2">{{ os === "mac" ? "No admin password and nothing opened on your Mac. It starts again by itself when you log in." : "No sudo needed, only python3. If this user can run Docker, the services found are also traced with eBPF - no code change. Opt out with AIOPS_EBPF=0." }}</p></div></li>
      <li :class="['step', { done: connected }]"><span class="n">3</span><div class="body"><h2>See it and its services appear</h2>
        <UiWait v-if="!host" :title="`Waiting for ${clean}…`" subtitle="This updates by itself." />
        <UiWait v-else-if="!connected" :title="`${clean} is registered`" subtitle="Waiting for its first measurements…" />
        <template v-else>
          <UiWait done :title="`${clean} is connected`">CPU {{ Math.round(host.cpu) }}% · Memory {{ Math.round(host.mem) }}% · Disk {{ Math.round(host.disk) }}%</UiWait>
          <div class="section-label">Services found on {{ clean }} ({{ services.length }})</div>
          <UiList><ServiceRow v-for="s in services" :key="s.service" :service="s" />
            <UiEmpty v-if="!services.length"><UiSpinner :size="16" /> Looking for listening ports and containers (about 1 minute)…</UiEmpty></UiList>
          <AutoTraceStatus class="mt" :host="host" :services="services" />
          <div class="row mt"><UiButton :to="`/computers/${clean}`">View {{ clean }}</UiButton><UiButton variant="tint" to="/map">See it on the map</UiButton></div>
        </template></div></li>
    </ol>
    <UiDisclosure class="mt" title="Advanced: server that already runs node_exporter">
      <p class="small muted">AIOps collects from it on port 9100, so it must be reachable from this server.</p>
      <UiField v-model="ne.name" label="Name" placeholder="db-01" />
      <UiField v-model="ne.address" label="Address" placeholder="10.4.82.30:9100" mono />
      <UiButton variant="tint" class="mt" @click="addNodeExporter">Add server</UiButton>
    </UiDisclosure>
  </div>
</template>
<style scoped>
.steps { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 14px; }
.step { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 18px 20px; display: grid; grid-template-columns: 32px minmax(0, 1fr); gap: 14px; }
.n { width: 28px; height: 28px; border-radius: 50%; background: var(--c-primary); color: #fff; font-weight: 700; font-size: 14px; display: grid; place-items: center; }
.step.done .n { background: var(--c-ok); }
.body { min-width: 0; } h2 { font-size: var(--fs-lg); margin: 2px 0 8px; }
.grid2 { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; }
.file { display: flex; align-items: center; gap: 10px; padding: 10px 12px; border: 1px dashed var(--c-text-3); border-radius: 10px; cursor: pointer; margin-bottom: 10px; }
.file input { max-width: 110px; }
@media (max-width: 640px) { .grid2 { grid-template-columns: 1fr; } }
.lbl { display: block; font-size: var(--fs-sm); color: var(--c-text-2); margin: 12px 0 6px; font-weight: 500; }
</style>
