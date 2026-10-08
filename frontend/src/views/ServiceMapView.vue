<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import BasePanel from "@/components/common/BasePanel.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
import { number, percent } from "@/utils/format";
const state = useAsyncState(api.serviceMap, 15000);
const rows = computed(() => {
  if (!state.data) return [];
  const byId = new Map(state.data.nodes.map((node) => [node.id, node]));
  const order: string[] = [];
  const visit = (id: string) => {
    if (order.includes(id)) return;
    order.push(id);
    state.data?.edges
      .filter((edge) => edge.from === id)
      .forEach((edge) => visit(edge.to));
  };
  state.data.entry.forEach(visit);
  state.data.nodes.forEach((node) => visit(node.id));
  return order.map((id) => byId.get(id)).filter(Boolean);
});
const isBad = (node: NonNullable<(typeof rows.value)[number]>) =>
  !!node.problem_id ||
  (node.error_rate ?? 0) > 0.05 ||
  node.instances?.some(
    (instance) => !!instance.problem_id || (instance.error_rate ?? 0) > 0.05,
  );
</script>
<template>
  <div class="page">
    <PageHeader
      title="Service map"
      description="Live request flow across connected services. Edge color reflects health and recent anomaly signals."
    /><LoadingState v-if="state.loading && !state.data" /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    /><BasePanel v-else-if="state.data" title="Current topology"
      ><div class="topology">
        <template v-for="(node, index) in rows" :key="node!.id"
          ><RouterLink
            class="node"
            :class="{ bad: isBad(node!) }"
            :to="node!.kind === 'network' ? '/map' : `/services/${node!.id}`"
            ><strong>{{ node!.id }}</strong
            ><span>{{
              isBad(node!)
                ? "anomaly detected"
                : node!.rps == null
                  ? "waiting for traffic"
                  : "healthy · live"
            }}</span
            ><small v-if="node!.rps != null"
              >{{ number(node!.rps) }} req/s ·
              {{ percent(node!.error_rate) }}</small
            >
            <div v-if="node!.instances?.length" class="instances">
              <em v-for="instance in node!.instances" :key="instance.id">{{
                instance.id
              }}</em>
            </div></RouterLink
          >
          <div v-if="index < rows.length - 1" class="edge">
            →<small
              >{{
                number(
                  state.data.edges.find((edge) => edge.from === node!.id)?.rps,
                )
              }}
              calls/s</small
            >
          </div></template
        >
      </div>
      <div class="legend">
        <span class="success-text">● healthy</span
        ><span class="danger-text">● anomaly</span
        ><span class="dim"
          >{{ state.data.traces_sampled }} traces sampled ·
          {{
            state.data.hosts.map((host) => host.name).join(", ") || "no hosts"
          }}</span
        >
      </div></BasePanel
    >
  </div>
</template>
<style scoped>
.topology {
  display: flex;
  min-height: 360px;
  align-items: center;
  gap: 12px;
  overflow-x: auto;
  padding: 40px 0;
}
.node {
  display: flex;
  width: 170px;
  min-width: 170px;
  min-height: 84px;
  flex-direction: column;
  gap: 4px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: white;
  padding: 12px;
}
.node.bad {
  border-color: #fecdd3;
  background: var(--color-status-danger-bg);
}
.node span,
.node small {
  font-size: 12px;
}
.node span {
  color: var(--color-status-success-text);
}
.node.bad span {
  color: var(--color-status-danger-text);
}
.node small {
  color: var(--color-text-muted);
}
.edge {
  display: flex;
  min-width: 62px;
  flex-direction: column;
  align-items: center;
  color: var(--color-text-dim);
}
.edge small {
  font-size: 10px;
  white-space: nowrap;
}
.instances {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.instances em {
  border-radius: 4px;
  background: var(--color-surface-subtle);
  padding: 2px 4px;
  font-size: 10px;
  font-style: normal;
}
.legend {
  display: flex;
  gap: 18px;
  font-size: 12px;
}
</style>
