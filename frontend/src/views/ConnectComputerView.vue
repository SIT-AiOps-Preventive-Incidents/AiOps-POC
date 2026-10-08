<script setup>
import { computed, ref, watch } from "vue";
import ServiceRow from "@/components/domain/ServiceRow.vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { slug } from "@/lib/format";
import { useCatalogStore } from "@/stores/catalog";
import { useUiStore } from "@/stores/ui";

const ui = useUiStore();
const cat = useCatalogStore();
const name = ref(ui.prefs.computerName || "my-mac");
const os = ref("mac");
const origin = window.location.origin;
const clean = computed(() => slug(name.value) || "my-mac");
const command = computed(() => `curl -fsSL ${origin}/install/agent.sh | AIOPS_HOST_NAME=${clean.value} sh`);
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
    <UiPageHeader title="Connect a computer" :back="{ to: '/connect', label: 'Connect' }" />
    <ol class="steps">
      <li class="step done"><span class="n">1</span><div class="body"><h2>Name it</h2>
        <UiField v-model="name" label="Computer name" />
        <label class="lbl">System</label>
        <UiSegmented v-model="os" :options="[{ value: 'mac', label: 'macOS', logo: 'apple' }, { value: 'linux', label: 'Linux', logo: 'linux' }]" label="System" /></div></li>
      <li class="step done"><span class="n">2</span><div class="body"><h2>Paste this in Terminal {{ os === "mac" ? "on the Mac" : "on the server" }}</h2>
        <UiCodeBlock :code="command" />
        <p class="small muted mt-2">{{ os === "mac" ? "No admin password and nothing opened on your Mac. It starts again by itself when you log in." : "No sudo needed, only python3. Docker containers are found if the user can run docker." }}</p></div></li>
      <li :class="['step', { done: connected }]"><span class="n">3</span><div class="body"><h2>See it and its services appear</h2>
        <UiWait v-if="!host" :title="`Waiting for ${clean}...`" subtitle="This updates by itself." />
        <UiWait v-else-if="!connected" :title="`${clean} is registered`" subtitle="Waiting for its first measurements..." />
        <template v-else>
          <UiWait done :title="`${clean} is connected`">CPU {{ Math.round(host.cpu) }}% · Memory {{ Math.round(host.mem) }}% · Disk {{ Math.round(host.disk) }}%</UiWait>
          <div class="section-label">Services found on {{ clean }} ({{ services.length }})</div>
          <UiList><ServiceRow v-for="s in services" :key="s.service" :service="s" />
            <UiEmpty v-if="!services.length"><UiSpinner :size="16" /> Looking for listening ports and containers (about 1 minute)...</UiEmpty></UiList>
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
