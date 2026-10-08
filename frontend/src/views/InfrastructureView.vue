<script setup lang="ts">
import { RouterLink } from "vue-router";
import BaseButton from "@/components/common/BaseButton.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
import { number } from "@/utils/format";
const state = useAsyncState(api.hosts, 10000);
</script>
<template>
  <div class="page">
    <PageHeader
      title="Infrastructure"
      description="Hosts connected via node_exporter or the AiOps agent. Prometheus discovers registry entries automatically."
      ><RouterLink to="/connect/computer"
        ><BaseButton>Connect infrastructure</BaseButton></RouterLink
      ></PageHeader
    ><LoadingState v-if="state.loading && !state.data" /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    />
    <div v-else-if="state.data?.length" class="hosts">
      <RouterLink
        v-for="host in state.data"
        :key="host.id"
        :to="`/infra/${host.name}`"
        class="host"
        ><div class="host__head">
          <strong :class="host.problem_id ? 'danger-text' : 'success-text'"
            >● {{ host.name }}</strong
          ><span>{{ host.address }}</span>
        </div>
        <small
          >{{ host.os }} ·
          {{
            host.agent === "aiops-agent" ? "AiOps agent" : "node_exporter"
          }}</small
        ><label
          >CPU {{ number(host.cpu) }}%<i
            ><b :style="{ width: `${host.cpu || 0}%` }" /></i></label
        ><label
          >Memory {{ number(host.mem) }}%<i
            ><b :style="{ width: `${host.mem || 0}%` }" /></i></label
        ><label
          >Disk {{ number(host.disk) }}%<i
            ><b :style="{ width: `${host.disk || 0}%` }" /></i></label
      ></RouterLink>
    </div>
    <EmptyState
      v-else
      title="No infrastructure connected"
      message="Install the agent or register a node_exporter host."
      ><RouterLink class="link" to="/connect/computer"
        >Connect infrastructure</RouterLink
      ></EmptyState
    >
  </div>
</template>
<style scoped>
.hosts {
  display: grid;
  grid-template-columns: repeat(3, minmax(280px, 1fr));
  gap: 16px;
}
.host {
  display: flex;
  min-height: 190px;
  flex-direction: column;
  gap: 9px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  background: white;
  padding: 16px;
}
.host:hover {
  border-color: var(--color-accent-primary);
}
.host__head {
  display: flex;
  justify-content: space-between;
}
.host__head span,
.host small {
  color: var(--color-text-muted);
  font-size: 12px;
}
.host label {
  font-size: 12px;
}
.host i {
  display: block;
  height: 5px;
  margin-top: 5px;
  border-radius: 3px;
  background: var(--color-surface-subtle);
}
.host b {
  display: block;
  height: 100%;
  max-width: 100%;
  border-radius: 3px;
  background: var(--color-status-success);
}
@media (max-width: 1050px) {
  .hosts {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 680px) {
  .hosts {
    grid-template-columns: 1fr;
  }
}
</style>
