<script setup>
import { ref } from "vue";
import { useRouter } from "vue-router";
import ProblemRow from "@/components/domain/ProblemRow.vue";
import TraceWaterfall from "@/components/domain/TraceWaterfall.vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { ago, clockSec, ms, pct } from "@/lib/format";
import { useCatalogStore } from "@/stores/catalog";
import { useUiStore } from "@/stores/ui";

const props = defineProps({ name: String });
const d = ref(null);
const ui = useUiStore();
const cat = useCatalogStore();
const router = useRouter();
usePolling(async () => { d.value = await api.services.get(props.name); }, 15000);
const trace = ref(null);
const openTrace = async (id) => { try { trace.value = await api.map.trace(id); } catch (e) { ui.toast(e.message); } };
const confirmRemove = ref(false);
async function remove() { await cat.removeService(props.name); router.push("/services"); }
</script>
<template>
  <div v-if="d" class="page">
    <UiPageHeader :title="d.service.display_name" :back="{ to: '/services', label: 'Services' }"
                  :subtitle="`${d.service.service_name} · owner ${d.service.owner || '-'}${d.health.version ? ` · v${d.health.version} (${d.health.commit})` : ''}${d.service.hosts.length ? ` · on ${d.service.hosts.join(', ')}` : ''}`">
      <UiButton v-if="d.health.problem_id" :to="`/problems/${d.health.problem_id}`">Open problem P-{{ d.health.problem_id }}</UiButton>
      <UiPill v-else :tone="d.health.status === 'healthy' ? 'ok' : 'neutral'">{{ d.health.status === "healthy" ? "Healthy" : "No data yet" }}</UiPill>
    </UiPageHeader>
    <div v-if="d.service.kind === 'process' || d.service.kind === 'external'" class="stack">
      <UiCard title="Discovered by the host agent">
        <p>This {{ d.service.kind === "external" ? "external dependency" : "process" }} was found on <b>{{ d.service.hosts.join(", ") || "-" }}</b>.
          AIOps knows it is running and who it talks to, but not its requests or errors.</p>
        <UiList plain class="mt"><UiListRow v-for="i in d.service.instances" :key="i.name" :title="i.name" :subtitle="`${i.pid ? `PID ${i.pid} · ` : ''}${i.port ? `port ${i.port} · ` : ''}seen ${ago(i.last_seen)}`" /></UiList>
        <UiButton class="mt" variant="tint" :to="{ path: '/connect/service', query: { name: d.service.service_name } }">Turn on tracing for this app</UiButton>
      </UiCard>
    </div>
    <template v-else>
      <div class="grid grid--3">
        <UiAreaChart title="Requests / s" :points="d.series.rps" />
        <UiAreaChart title="Error rate" :points="d.series.error_rate" color="var(--c-chart-2)" :format="(v) => pct(v)" />
        <UiAreaChart title="Response time (p95)" :points="d.series.p95" color="var(--c-chart-3)" :format="ms" />
      </div>
      <div class="grid grid--2 mt">
        <div>
          <div class="section-label">Endpoints</div>
          <UiList plain><UiListRow v-for="e in d.endpoints" :key="e.name"><template #title><span class="mono">{{ e.name }}</span></template>
            <template #accessory>{{ e.rps }}/s · <span :class="{ bad: e.error_rate > 0.05 }">{{ pct(e.error_rate) }}</span></template></UiListRow>
            <UiEmpty v-if="!d.endpoints.length">No requests yet</UiEmpty></UiList>
          <div class="section-label">Errors by version</div>
          <UiList plain><UiListRow v-for="v in d.versions" :key="v.commit" :title="`v${v.version}`" :subtitle="v.commit">
            <template #accessory><span :class="{ bad: v.error_rate > 0.05 }">{{ pct(v.error_rate) }}</span></template></UiListRow>
            <UiEmpty v-if="!d.versions.length">No version data</UiEmpty></UiList>
        </div>
        <div>
          <div class="section-label">Recent traces</div>
          <UiList plain><UiListRow v-for="t in d.traces.slice(0, 8)" :key="t.traceID" :title="t.rootTraceName" :subtitle="`${t.rootServiceName} · ${clockSec(t.startTimeUnixNano / 1e9)}`" chevron @click="openTrace(t.traceID)">
            <template #accessory>{{ t.durationMs ?? 0 }} ms</template></UiListRow><UiEmpty v-if="!d.traces.length">No traces yet</UiEmpty></UiList>
          <div class="section-label">Deployments</div>
          <UiList plain><UiListRow v-for="x in d.deployments.slice(0, 6)" :key="x.id" :title="`v${x.version} · ${x.commit_hash}`" :subtitle="`${x.author} · ${x.message}`">
            <template #accessory>{{ ago(x.ts) }}</template></UiListRow><UiEmpty v-if="!d.deployments.length">No deployments recorded</UiEmpty></UiList>
        </div>
      </div>
      <div class="section-label">Logs (15 min)</div>
      <UiCard><div v-for="(l, i) in d.logs" :key="i" class="log"><span class="dim">{{ clockSec(l.ts) }}</span><span :class="['lv', l.level]">{{ l.level }}</span><span>{{ l.line }}</span></div>
        <UiEmpty v-if="!d.logs.length">No logs in the last 15 minutes</UiEmpty></UiCard>
    </template>
    <template v-if="d.incidents.length"><div class="section-label">Problems</div><UiList><ProblemRow v-for="p in d.incidents" :key="p.id" :incident="p" /></UiList></template>
    <UiButton class="mt" variant="danger" size="sm" @click="confirmRemove = true">Remove this service</UiButton>
    <UiSheet :model-value="!!trace" title="Request trace" :width="980" @update:model-value="trace = null"><TraceWaterfall :spans="trace || []" /></UiSheet>
    <UiSheet v-model="confirmRemove" :title="`Remove ${d.service.service_name}?`">
      <p class="muted">AIOps stops raising problems for it. Its history stays.</p>
      <template #footer><UiButton variant="plain" @click="confirmRemove = false">Cancel</UiButton><UiButton variant="tint" class="danger-btn" @click="remove">Remove</UiButton></template>
    </UiSheet>
  </div>
</template>
<style scoped>
.log { font: 12px/1.5 var(--font-mono); padding: 4px 0; border-bottom: 0.5px solid var(--c-separator); display: flex; gap: 10px; }
.lv { width: 64px; flex: none; font-weight: 600; color: var(--c-text-3); }
.lv.ERROR { color: var(--c-bad-text); } .lv.WARN, .lv.WARNING { color: var(--c-warn-text); }
.danger-btn { color: var(--c-bad-text); background: var(--c-bad-bg); }
</style>
