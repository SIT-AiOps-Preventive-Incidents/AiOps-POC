<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import ServiceRow from "@/components/domain/ServiceRow.vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { num } from "@/lib/format";
import { useCatalogStore } from "@/stores/catalog";

const props = defineProps({ name: String });
const d = ref(null);
const cat = useCatalogStore();
const router = useRouter();
usePolling(async () => { d.value = await api.hosts.get(props.name); }, 15000);
const confirmRemove = ref(false);
const pct0 = (v) => `${Math.round(v)}%`;
const origin = window.location.origin;
async function remove() { await cat.removeHost(props.name); router.push("/computers"); }
</script>
<template>
  <div v-if="d" class="page">
    <UiPageHeader :title="d.host.name" :back="{ to: '/computers', label: 'Computers' }"
                  :subtitle="`${d.host.os} · ${d.host.agent === 'aiops-agent' ? 'AIOps agent' : d.host.address} · owner ${d.host.owner || '-'}`">
      <UiButton v-if="d.host.problem_id" :to="`/problems/${d.host.problem_id}`">Open problem P-{{ d.host.problem_id }}</UiButton>
      <UiPill v-else :tone="d.host.status === 'healthy' ? 'ok' : 'neutral'">{{ d.host.status === "healthy" ? "Online" : d.host.status }}</UiPill>
      <UiButton variant="tint" icon="flowchart" :to="{ path: '/map' }">On the map</UiButton>
    </UiPageHeader>
    <div class="grid grid--4">
      <UiAreaChart title="CPU" :points="d.series.cpu" :format="pct0" />
      <UiAreaChart title="Memory" :points="d.series.mem" color="var(--c-chart-4)" :format="pct0" />
      <UiAreaChart title="Disk" :points="d.series.disk" color="var(--c-chart-5)" :format="pct0" />
      <UiAreaChart title="Load (1 min)" :points="d.series.load" color="var(--c-chart-3)" />
    </div>
    <div class="section-label">Services on this computer ({{ d.services.length }})</div>
    <UiList><ServiceRow v-for="s in d.services" :key="s.service" :service="s" />
      <UiEmpty v-if="!d.services.length">Nothing found yet. The agent reports listening ports and containers every minute.</UiEmpty></UiList>
    <template v-if="d.processes.length">
      <div class="section-label">Busiest processes</div>
      <UiList plain><UiListRow v-for="p in d.processes" :key="p.pid" :title="p.name" :subtitle="`PID ${p.pid}`">
        <template #accessory>CPU {{ num(p.cpu) }}% · Memory {{ num(p.mem) }}%</template></UiListRow></UiList>
    </template>
    <template v-if="d.containers.length">
      <div class="section-label">Containers</div>
      <UiList plain><UiListRow v-for="c in d.containers" :key="c.name" :title="c.name" :subtitle="c.image">
        <template #accessory><span :class="{ bad: c.cpu_pct > 50 }">CPU {{ num(c.cpu_pct) }}% · {{ num(c.mem_mb, 0) }} MB</span></template></UiListRow></UiList>
    </template>
    <UiButton class="mt" variant="danger" size="sm" @click="confirmRemove = true">Remove this computer</UiButton>
    <UiSheet v-model="confirmRemove" :title="`Remove ${d.host.name}?`">
      <p class="muted">AIOps stops watching it. To also stop the agent, run this on that machine:</p>
      <UiCodeBlock class="mt" :code="`curl -fsSL ${origin}/install/uninstall.sh | sh`" />
      <template #footer><UiButton variant="plain" @click="confirmRemove = false">Cancel</UiButton><UiButton variant="danger" @click="remove">Remove</UiButton></template>
    </UiSheet>
  </div>
</template>
