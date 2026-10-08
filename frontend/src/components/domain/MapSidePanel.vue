<script setup>
import { computed } from "vue";
import { ago, ms, num, pct } from "@/lib/format";
import { languageLogo } from "@/lib/vocab";
import { useMapStore } from "@/stores/map";
const map = useMapStore();
const node = computed(() => map.data?.nodes.find((n) => n.id === map.selected) || (map.selected === "clients" ? { id: "clients", kind: "client", instances: [], hosts: [] } : null));
const edges = computed(() => {
  const all = [...(map.data?.edges || []), ...(map.data?.entry || []).map((r) => ({ from: "clients", to: r, type: "traced" }))];
  return { in: all.filter((e) => e.to === map.selected), out: all.filter((e) => e.from === map.selected) };
});
const rate = (e) => (e.rps != null ? `${num(e.rps)}/s` : "network");
</script>
<template>
  <aside v-if="node" class="side stack">
    <UiCard>
      <div class="row row--between">
        <div class="row"><UiAppTile :logo="languageLogo(node.kind === 'network' ? 'nginx' : node.language)" :icon="node.kind === 'client' ? 'globe' : 'apps'" :size="36" />
          <div><h2>{{ node.id === "clients" ? "Clients" : node.name || node.id }}</h2>
            <div class="small muted">{{ node.kind === "process" ? "Discovered process" : node.kind === "external" ? "External dependency" : node.kind === "network" ? "Network device" : node.kind === "client" ? "Users" : "Service" }}{{ node.owner ? ` · ${node.owner}` : "" }}</div></div></div>
        <UiButton variant="plain" size="sm" @click="map.select(null)">Done</UiButton>
      </div>
      <div v-if="node.rps != null" class="grid grid--3 mt">
        <div><div class="small muted">Requests</div><b>{{ num(node.rps) }}/s</b></div>
        <div><div class="small muted">Errors</div><b :class="{ bad: node.error_rate > 0.05 }">{{ pct(node.error_rate) }}</b></div>
        <div><div class="small muted">p95</div><b>{{ ms(node.p95_ms) }}</b></div>
      </div>
      <p v-else-if="node.kind === 'process' || node.kind === 'external'" class="small muted mt">
        Found by the agent on {{ node.hosts.join(", ") || "-" }} · last seen {{ ago(node.last_seen) }}.
        Turn on OpenTelemetry in this app to see its requests and errors.</p>
      <template v-if="node.instances?.length">
        <div class="small muted mt">Instances behind the load balancer</div>
        <UiMeter v-for="i in node.instances" :key="i.id" :label="i.id" :value="(i.rps / (node.rps || 1)) * 100" :warn="101" :crit="101" />
      </template>
      <div v-if="node.hosts?.length" class="small mt">Runs on <router-link v-for="h in node.hosts" :key="h" :to="`/computers/${h}`">{{ h }} </router-link></div>
      <div class="row row--wrap mt">
        <UiButton v-if="node.problem_id" :to="`/problems/${node.problem_id}`">Open problem P-{{ node.problem_id }}</UiButton>
        <UiButton v-if="node.kind !== 'client'" variant="tint" :to="`/services/${node.id}`">Details</UiButton>
        <UiButton v-if="node.kind === 'process'" variant="tint" :to="{ path: '/connect/service', query: { name: node.id } }">Turn on tracing</UiButton>
      </div>
    </UiCard>
    <template v-for="[title, list, key] in [['Called by', edges.in, 'from'], ['Calls', edges.out, 'to']]" :key="title">
      <div v-if="list.length"><div class="section-label">{{ title }}</div>
        <UiList plain><UiListRow v-for="e in list" :key="e[key]" :title="e[key] === 'clients' ? 'Clients' : e[key]" chevron @click="map.select(e[key])">
          <template #accessory>{{ rate(e) }}</template></UiListRow></UiList></div>
    </template>
  </aside>
</template>
<style scoped>
.side { position: sticky; top: 12px; }
h2 { font-size: var(--fs-lg); }
</style>
