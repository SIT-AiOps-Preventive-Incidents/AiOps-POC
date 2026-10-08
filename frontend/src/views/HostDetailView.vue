<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter, RouterLink } from "vue-router";
import BaseButton from "@/components/common/BaseButton.vue";
import BasePanel from "@/components/common/BasePanel.vue";
import ChartCard from "@/components/common/ChartCard.vue";
import ConfirmDialog from "@/components/common/ConfirmDialog.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import StatusChip from "@/components/common/StatusChip.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
import { useUiStore } from "@/stores/ui";
import { metricPercent, number } from "@/utils/format";
const route = useRoute(),
  router = useRouter(),
  ui = useUiStore();
const state = useAsyncState(() => api.host(String(route.params.name)), 15000);
const confirm = ref(false),
  busy = ref(false);
async function remove() {
  if (!state.data) return;
  busy.value = true;
  try {
    await api.deleteHost(state.data.host.id);
    ui.notify("Computer removed");
    router.push("/infra");
  } catch (e) {
    ui.notify(e instanceof Error ? e.message : "Could not remove computer");
  } finally {
    busy.value = false;
    confirm.value = false;
  }
}
</script>
<template>
  <div class="page">
    <LoadingState v-if="state.loading && !state.data" /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    /><template v-else-if="state.data"
      ><RouterLink class="back" to="/infra">‹ Computers</RouterLink
      ><PageHeader
        :title="state.data.host.name"
        :description="`${state.data.host.os || ''} · ${state.data.host.agent === 'aiops-agent' ? 'AiOps agent' : state.data.host.address} · owner ${state.data.host.owner || '—'}`"
        ><RouterLink
          v-if="state.data.host.problem_id"
          :to="`/problems/${state.data.host.problem_id}`"
          ><BaseButton
            >Open problem P-{{ state.data.host.problem_id }}</BaseButton
          ></RouterLink
        ><StatusChip
          v-else
          :tone="state.data.host.status === 'healthy' ? 'success' : 'neutral'"
          >{{
            state.data.host.status === "healthy"
              ? "Online"
              : state.data.host.status
          }}</StatusChip
        ></PageHeader
      >
      <div class="charts">
        <ChartCard
          label="CPU"
          :value="metricPercent(state.data.host.cpu)"
          :points="state.data.series.cpu"
        /><ChartCard
          label="Memory"
          :value="metricPercent(state.data.host.mem)"
          :points="state.data.series.mem"
          color="#9b5cff"
        /><ChartCard
          label="Disk"
          :value="metricPercent(state.data.host.disk)"
          :points="state.data.series.disk"
          color="#00b4c5"
        /><ChartCard
          label="Load (1 min)"
          :value="number(state.data.host.load)"
          :points="state.data.series.load"
          color="#f59e0b"
        />
      </div>
      <BasePanel title="Busiest processes" flush
        ><div v-if="state.data.processes.length" class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Process</th>
                <th>PID</th>
                <th>CPU</th>
                <th>Memory</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="p in state.data.processes" :key="p.pid">
                <td>{{ p.name }}</td>
                <td>{{ p.pid }}</td>
                <td>{{ number(p.cpu) }}%</td>
                <td>{{ number(p.mem) }}%</td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else title="No process data" /></BasePanel
      ><BasePanel v-if="state.data.containers.length" title="Containers" flush
        ><div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Image</th>
                <th>CPU</th>
                <th>Memory</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in state.data.containers" :key="c.name">
                <td>{{ c.name }}</td>
                <td>
                  <code>{{ c.image }}</code>
                </td>
                <td>{{ number(c.cpu_pct) }}%</td>
                <td>{{ number(c.mem_mb, 0) }} MB</td>
              </tr>
            </tbody>
          </table>
        </div></BasePanel
      ><BaseButton class="remove" variant="danger" @click="confirm = true"
        >Remove this computer</BaseButton
      ></template
    ><ConfirmDialog
      :open="confirm"
      title="Remove computer?"
      message="AIOps will stop monitoring it. The agent must be uninstalled separately on the computer."
      confirm-label="Remove"
      danger
      :busy="busy"
      @cancel="confirm = false"
      @confirm="remove"
    />
  </div>
</template>
<style scoped>
.back {
  display: inline-block;
  margin-bottom: 8px;
  color: var(--color-accent-primary);
}
.charts {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.page > :deep(.panel) + :deep(.panel) {
  margin-top: 16px;
}
.remove {
  margin-top: 16px;
}
@media (max-width: 1050px) {
  .charts {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 600px) {
  .charts {
    grid-template-columns: 1fr;
  }
}
</style>
