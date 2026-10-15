<script setup>
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import AutoTraceStatus from "@/components/domain/AutoTraceStatus.vue";
import ServiceRow from "@/components/domain/ServiceRow.vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { progress, removal } from "@/lib/connect";
import { num } from "@/lib/format";
import { useCatalogStore } from "@/stores/catalog";
import { useUiStore } from "@/stores/ui";

const props = defineProps({ name: String });
const d = ref(null);
const cat = useCatalogStore();
const ui = useUiStore();
const router = useRouter();
const gone = ref(false);
const now = ref(Date.now() / 1000);
let last = 0;
usePolling(async () => {
  now.value = Date.now() / 1000;
  if (!d.value?.host.uninstall_requested_at && now.value - last < 15) return;   // the page is heavy: every 15 s, every 3 s only while removing
  last = now.value;
  try {
    d.value = await api.hosts.get(props.name);
  } catch (e) {
    if (e.status === 404 && d.value?.host.uninstall_requested_at) gone.value = true;   // the agent removed itself
    else throw e;
  }
}, 3000);
const confirmRemove = ref(false);
const pct0 = (v) => `${Math.round(v)}%`;
const origin = window.location.origin;
const isAgent = computed(() => d.value?.host.agent === "aiops-agent");
const job = computed(() => removal({ requestedAt: d.value?.host.uninstall_requested_at, now: now.value, gone: gone.value }));
const ring = computed(() => progress(job.value));
async function removeAgent() {
  try {
    const r = await api.hosts.uninstall(props.name);
    if (r.state === "removed") return done();
    d.value = await api.hosts.get(props.name);
  } catch (e) {
    ui.toast(e.message);
  }
}
async function forget() { await cat.removeHost(props.name); done(); }
function done() { confirmRemove.value = false; ui.toast(`${props.name} removed`); router.push("/computers"); }
</script>
<template>
  <div v-if="d" class="page">
    <UiPageHeader :title="d.host.name" :back="{ to: '/computers', label: 'Hosts' }"
                  :subtitle="`${d.host.os} · ${d.host.agent === 'aiops-agent' ? 'AIOps agent' : d.host.address} · owner ${d.host.owner || '-'}`">
      <UiButton v-if="d.host.problem_id" :to="`/problems/${d.host.problem_id}`">Open problem P-{{ d.host.problem_id }}</UiButton>
      <UiPill v-else :tone="d.host.status === 'healthy' ? 'ok' : 'neutral'">{{ d.host.status === "healthy" ? "Online" : d.host.status }}</UiPill>
      <UiButton variant="tint" icon="flowchart" :to="{ path: '/map' }">On the map</UiButton>
      <UiButton variant="danger" icon="dismiss" @click="confirmRemove = true">{{ isAgent ? "Remove agent" : "Remove" }}</UiButton>
    </UiPageHeader>
    <div class="grid grid--4">
      <UiAreaChart title="CPU" :points="d.series.cpu" :format="pct0" :normal="d.normal?.cpu" />
      <UiAreaChart title="Memory" :points="d.series.mem" color="var(--c-chart-4)" :format="pct0" :normal="d.normal?.mem" />
      <UiAreaChart title="Disk" :points="d.series.disk" color="var(--c-chart-5)" :format="pct0" :normal="d.normal?.disk" />
      <UiAreaChart title="Load (1 min)" :points="d.series.load" color="var(--c-chart-3)" />
    </div>
    <div class="section-label">Services on this computer ({{ d.services.length }})</div>
    <UiList><ServiceRow v-for="s in d.services" :key="s.service" :service="s" />
      <UiEmpty v-if="!d.services.length">Nothing found yet. The agent reports listening ports and containers every minute.</UiEmpty></UiList>
    <AutoTraceStatus v-if="d.host.agent === 'aiops-agent'" class="mt" :host="d.host" :services="d.services" />
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
    <UiSheet v-model="confirmRemove" :title="isAgent ? `Remove the agent from ${d.host.name}?` : `Remove ${d.host.name}?`">
      <template v-if="!isAgent"><p class="muted">AIOps stops watching it. Nothing of AIOps runs on that machine.</p></template>
      <template v-else-if="!job">
        <p class="muted">On its next report (within a minute) the agent removes everything AIOps put on {{ d.host.name }}: the log collector, the eBPF tracer, its autostart and the platform key. Then the server disappears from AIOps. Nothing else on the server is touched.</p>
      </template>
      <template v-else>
        <div class="removing">
          <UiProgressRing :value="ring.value" :state="ring.state" :size="72" />
          <div><b>{{ job.state === "done" ? "Removed" : job.state === "failed" ? "The agent did not answer" : `${ring.label}…` }}</b>
            <div class="small muted">{{ job.state === "failed" ? "The server may be off, or its agent is older than 1.4." : `Asked ${Math.round(now - d.host.uninstall_requested_at)} s ago` }}</div></div>
        </div>
        <ol class="checklist">
          <li v-for="s in job.steps" :key="s.key" :class="s.state">
            <UiIcon v-if="s.state === 'done'" name="checkmark_circle" filled :size="18" />
            <UiIcon v-else-if="s.state === 'failed'" name="dismiss" :size="18" />
            <span v-else class="dot" />{{ s.label }}</li>
        </ol>
        <template v-if="job.state === 'failed'">
          <p class="small muted mt-2">Run this on {{ d.host.name }} to remove it by hand, then forget it here:</p>
          <UiCodeBlock :code="`curl -fsSL ${origin}/install/uninstall.sh | sh`" />
        </template>
      </template>
      <template #footer>
        <UiButton variant="plain" @click="confirmRemove = false">{{ job ? "Close" : "Cancel" }}</UiButton>
        <UiButton v-if="!isAgent" variant="danger" @click="forget">Remove</UiButton>
        <UiButton v-else-if="!job" variant="danger" @click="removeAgent">Remove agent</UiButton>
        <UiButton v-else-if="job.state === 'failed'" variant="danger" @click="forget">Forget it anyway</UiButton>
        <UiButton v-else-if="job.state === 'done'" @click="done">Done</UiButton>
      </template>
    </UiSheet>
  </div>
  <div v-else class="page"><UiPageHeader :title="name" subtitle="Loading…" :back="{ to: '/computers', label: 'Hosts' }" /></div>
</template>
<style scoped>
.removing { display: flex; align-items: center; gap: 16px; }
.checklist { list-style: none; padding: 0; margin: 16px 0 0; display: grid; gap: 8px; }
.checklist li { display: flex; align-items: center; gap: 10px; color: var(--c-text-3); }
.checklist li.done { color: var(--c-ok-text); }
.checklist li.running { color: var(--c-text); font-weight: var(--fw-semibold); }
.checklist li.failed { color: var(--c-bad-text); }
.dot { width: 18px; height: 18px; border-radius: 50%; border: 2px solid currentColor; flex: none; }
.checklist li.running .dot { border-color: var(--c-primary); background: radial-gradient(var(--c-primary) 35%, transparent 40%); }
</style>
