<script setup>
import { computed, ref, watch } from "vue";
import AutoTraceStatus from "@/components/domain/AutoTraceStatus.vue";
import ServiceRow from "@/components/domain/ServiceRow.vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { installCommand, tunnelCommand } from "@/lib/connect";
import { slug } from "@/lib/format";
import { useCatalogStore } from "@/stores/catalog";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const cat = useCatalogStore();
const name = ref(ui.prefs.computerName || "my-mac");
const os = ref("mac");
const origin = window.location.origin;
const clean = computed(() => slug(name.value) || "my-mac");
const reach = ref("direct");
const login = ref("");
const tunnel = computed(() => os.value === "linux" && reach.value === "tunnel");
const command = computed(() => installCommand({ origin, name: clean.value, tunnel: tunnel.value }));
const tunnelCmd = computed(() => tunnelCommand({ login: login.value.trim() }));
watch(clean, (v) => ui.setPref("computerName", v));

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
          <label class="lbl">How it reaches AIOps</label>
          <UiSegmented v-model="reach" :options="[{ value: 'direct', label: 'Directly (campus or VPN)' }, { value: 'tunnel', label: 'Through an SSH tunnel' }]" label="Reach" />
          <template v-if="tunnel">
            <UiField v-model="login" label="SSH login of the server" placeholder="poc@34.2.129.3" mono class="mt" />
            <p class="small muted">For a server outside the campus network, such as a cloud VM. AIOps connects out to it; nothing is opened on the server and the tunnel only listens on its loopback.</p>
          </template>
        </template></div></li>
      <li v-if="tunnel" class="step done"><span class="n">2</span><div class="body"><h2>On the AIOps server, open the tunnel</h2>
        <UiCodeBlock :code="tunnelCmd" />
        <p class="small muted mt-2">Keep it running (for example as a systemd service). The server then reaches AIOps on 127.0.0.1:18080 and 127.0.0.1:14318.</p></div></li>
      <li class="step done"><span class="n">{{ tunnel ? 3 : 2 }}</span><div class="body"><h2>Paste this in Terminal {{ os === "mac" ? "on the Mac" : "on the server" }}</h2>
        <UiCodeBlock :code="command" />
        <p class="small muted mt-2">{{ os === "mac" ? "No admin password and nothing opened on your Mac. It starts again by itself when you log in." : "No sudo needed, only python3. If this user can run Docker, the services found are also traced with eBPF - no code change. Opt out with AIOPS_EBPF=0." }}</p></div></li>
      <li :class="['step', { done: connected }]"><span class="n">{{ tunnel ? 4 : 3 }}</span><div class="body"><h2>See it and its services appear</h2>
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
.lbl { display: block; font-size: var(--fs-sm); color: var(--c-text-2); margin: 12px 0 6px; font-weight: 500; }
</style>
