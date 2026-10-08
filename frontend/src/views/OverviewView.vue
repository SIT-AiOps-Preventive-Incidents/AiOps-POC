<script setup lang="ts">
import { computed } from "vue";
import { RouterLink } from "vue-router";
import BasePanel from "@/components/common/BasePanel.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import MetricCard from "@/components/common/MetricCard.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import ProblemCard from "@/components/common/ProblemCard.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
import { duration, milliseconds, number, percent } from "@/utils/format";

const state = useAsyncState(api.overview, 10000);
const flow = computed(() => {
  const services =
    state.data?.services.map(
      (service) => service.service || service.service_name,
    ) ?? [];
  return ["edge-firewall", "edge-lb", "frontend", "checkout", "payment"].filter(
    (name) => services.includes(name),
  );
});
</script>
<template>
  <div class="page">
    <PageHeader
      title="Environment overview"
      description="Customer services and infrastructure connected to the platform, monitored in real time by the anomaly detector and agentic RCA pipeline."
    /><LoadingState v-if="state.loading && !state.data" /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    /><template v-else-if="state.data"
      ><div class="metrics">
        <MetricCard
          label="Open problems"
          :value="state.data.kpi.open"
          :meta="`${state.data.kpi.awaiting_approval} awaiting approval`"
          :tone="state.data.kpi.open ? 'danger' : 'success'"
        /><MetricCard
          label="Mean time to detect"
          :value="duration(state.data.kpi.mttd_s)"
          meta="anomaly start to problem"
        /><MetricCard
          label="Mean time to RCA"
          :value="duration(state.data.kpi.mtta_s)"
          meta="problem to AI report"
        /><MetricCard
          label="Mean time to resolve"
          :value="duration(state.data.kpi.mttr_s)"
          meta="problem to verified fix"
        /><MetricCard
          label="Avg RCA score"
          :value="
            state.data.kpi.avg_score ? `${state.data.kpi.avg_score} / 5` : '—'
          "
          :meta="`${state.data.kpi.total} problems total`"
        />
      </div>
      <div class="overview-grid">
        <BasePanel title="Services"
          ><div v-if="state.data.services.length" class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Service</th>
                  <th>Version</th>
                  <th>Req/s</th>
                  <th>P95</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="service in state.data.services.slice(0, 6)"
                  :key="service.service_name"
                >
                  <td>
                    <RouterLink
                      class="link"
                      :to="`/services/${service.service || service.service_name}`"
                      >{{ service.name }}</RouterLink
                    >
                  </td>
                  <td>{{ service.version ? `v${service.version}` : "—" }}</td>
                  <td>{{ number(service.rps) }}</td>
                  <td>{{ milliseconds(service.p95_ms) }}</td>
                  <td
                    :class="service.problem_id ? 'danger-text' : 'success-text'"
                  >
                    {{
                      service.problem_id
                        ? `P-${service.problem_id}`
                        : service.status || "—"
                    }}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <EmptyState v-else title="No services connected"
            ><RouterLink class="link" to="/connect/service"
              >Connect a service</RouterLink
            ></EmptyState
          ></BasePanel
        ><BasePanel title="Open problems"
          ><div v-if="state.data.open_problems.length" class="problems">
            <ProblemCard
              v-for="problem in state.data.open_problems.slice(0, 2)"
              :key="problem.id"
              :problem="problem"
            />
          </div>
          <EmptyState
            v-else
            title="Everything is healthy"
            message="No open problems require attention."
        /></BasePanel>
      </div>
      <BasePanel title="Hosts"
        ><div v-if="state.data.hosts.length" class="hosts">
          <RouterLink
            v-for="host in state.data.hosts"
            :key="host.id"
            :to="`/infra/${host.name}`"
            class="host"
            ><div>
              <strong :class="host.problem_id ? 'danger-text' : 'success-text'"
                >● {{ host.name }}</strong
              ><span>{{ host.address }}</span>
            </div>
            <small
              >CPU {{ number(host.cpu) }}% · Memory {{ number(host.mem) }}% ·
              Disk {{ number(host.disk) }}%</small
            >
            <div class="meters">
              <i :style="{ width: `${host.cpu || 0}%` }" /><i
                :style="{ width: `${host.mem || 0}%` }"
              /><i :style="{ width: `${host.disk || 0}%` }" /></div
          ></RouterLink>
        </div>
        <EmptyState v-else title="No hosts connected" /></BasePanel
      ><BasePanel title="Service flow"
        ><div v-if="flow.length" class="flow">
          <template v-for="(node, index) in flow" :key="node"
            ><RouterLink
              :to="node.startsWith('edge-') ? '/map' : `/services/${node}`"
              >{{ node }}</RouterLink
            ><span v-if="index < flow.length - 1">→</span></template
          >
        </div>
        <span v-else class="muted"
          >Topology appears after traces arrive.</span
        ></BasePanel
      ></template
    >
  </div>
</template>
<style scoped>
.metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.overview-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.7fr) minmax(320px, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.problems {
  display: grid;
  gap: 10px;
}
.hosts {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}
.host {
  width: 370px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  padding: 12px;
}
.host > div:first-child {
  display: flex;
  justify-content: space-between;
}
.host span,
.host small {
  color: var(--color-text-muted);
  font-size: 12px;
}
.meters {
  display: grid;
  gap: 4px;
  margin-top: 8px;
}
.meters i {
  display: block;
  height: 5px;
  max-width: 100%;
  border-radius: 3px;
  background: var(--color-status-success);
}
.flow {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.flow a {
  border: 1px solid var(--color-border-default);
  border-radius: 999px;
  padding: 4px 10px;
  color: var(--color-text-muted);
  font-size: 12px;
}
.page > :deep(.panel) + :deep(.panel) {
  margin-top: 16px;
}
@media (max-width: 1100px) {
  .metrics {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 840px) {
  .overview-grid {
    grid-template-columns: 1fr;
  }
  .metrics {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 520px) {
  .metrics {
    grid-template-columns: 1fr;
  }
}
</style>
