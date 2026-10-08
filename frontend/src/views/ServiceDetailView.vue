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
import { ago, milliseconds, number, percent, time } from "@/utils/format";
const route = useRoute(),
  router = useRouter(),
  ui = useUiStore();
const name = String(route.params.service);
const state = useAsyncState(() => api.service(name), 15000);
const confirm = ref(false),
  busy = ref(false),
  trace = ref<Awaited<ReturnType<typeof api.traces>> | null>(null);
async function remove() {
  if (!state.data) return;
  busy.value = true;
  try {
    await api.deleteApp(state.data.app.id);
    ui.notify("Service removed");
    router.push("/services");
  } catch (e) {
    ui.notify(e instanceof Error ? e.message : "Could not remove service");
  } finally {
    busy.value = false;
    confirm.value = false;
  }
}
async function showTrace(id: string) {
  try {
    trace.value = await api.traces(id);
    if (!trace.value.length) ui.notify("Trace not available yet");
  } catch (e) {
    ui.notify(e instanceof Error ? e.message : "Could not load trace");
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
      ><RouterLink class="back" to="/services">‹ Services</RouterLink
      ><PageHeader
        :title="state.data.app.name"
        :description="`${state.data.app.service_name} · owner ${state.data.app.owner || state.data.app.team || '—'}${state.data.health.version ? ` · v${state.data.health.version} (${state.data.health.commit || ''})` : ''}`"
        ><RouterLink
          v-if="state.data.health.problem_id"
          :to="`/problems/${state.data.health.problem_id}`"
          ><BaseButton
            >Open problem P-{{ state.data.health.problem_id }}</BaseButton
          ></RouterLink
        ><StatusChip
          v-else
          :tone="state.data.health.status === 'healthy' ? 'success' : 'neutral'"
          >{{
            state.data.health.status === "healthy" ? "Healthy" : "No data yet"
          }}</StatusChip
        ></PageHeader
      >
      <div class="charts">
        <ChartCard
          label="Requests / s"
          :value="number(state.data.health.rps)"
          :points="state.data.series.rps"
        /><ChartCard
          label="Error rate"
          :value="percent(state.data.health.error_rate)"
          :points="state.data.series.error_rate"
          color="#f0445e"
        /><ChartCard
          label="Response time (p95)"
          :value="milliseconds(state.data.health.p95_ms)"
          :points="state.data.series.p95"
          color="#f59e0b"
        />
      </div>
      <div class="cols">
        <div>
          <BasePanel title="Endpoints" flush
            ><div v-if="state.data.endpoints.length" class="table-wrap">
              <table class="data-table">
                <tbody>
                  <tr v-for="e in state.data.endpoints" :key="e.name">
                    <td>
                      <code>{{ e.name }}</code>
                    </td>
                    <td>{{ number(e.rps) }}/s</td>
                    <td :class="e.error_rate > 0.05 ? 'danger-text' : ''">
                      {{ percent(e.error_rate) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <EmptyState v-else title="No requests yet" /></BasePanel
          ><BasePanel title="Errors by version" flush
            ><div v-if="state.data.versions.length" class="table-wrap">
              <table class="data-table">
                <tbody>
                  <tr
                    v-for="v in state.data.versions"
                    :key="v.version + v.commit"
                  >
                    <td>v{{ v.version }}</td>
                    <td>
                      <code>{{ v.commit }}</code>
                    </td>
                    <td :class="v.error_rate > 0.05 ? 'danger-text' : ''">
                      {{ percent(v.error_rate) }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <EmptyState v-else title="No version data"
          /></BasePanel>
        </div>
        <div>
          <BasePanel title="Recent traces"
            ><button
              v-for="t in state.data.traces.slice(0, 8)"
              :key="t.traceID"
              class="row"
              @click="showTrace(t.traceID)"
            >
              <span
                ><b>{{ t.rootTraceName }}</b
                ><small
                  >{{ t.rootServiceName }} ·
                  {{ time(t.startTimeUnixNano / 1e9) }}</small
                ></span
              ><em>{{ milliseconds(t.durationMs) }}</em></button
            ><EmptyState
              v-if="!state.data.traces.length"
              title="No traces yet" /></BasePanel
          ><BasePanel title="Deployments"
            ><div
              v-for="d in state.data.deployments.slice(0, 6)"
              :key="d.id"
              class="row static"
            >
              <span
                ><b
                  >v{{ d.version }} · <code>{{ d.commit_hash }}</code></b
                ><small>{{ d.author }} · {{ d.message }}</small></span
              ><em>{{ ago(d.ts) }}</em>
            </div>
            <EmptyState
              v-if="!state.data.deployments.length"
              title="No deployments recorded"
          /></BasePanel>
        </div>
      </div>
      <BasePanel title="Logs"
        ><div v-if="state.data.logs.length" class="logs">
          <div v-for="log in state.data.logs" :key="`${log.ts}-${log.line}`">
            <time>{{ time(log.ts) }}</time
            ><b>{{ log.level || "info" }}</b
            ><span>{{ log.line }}</span>
          </div>
        </div>
        <EmptyState v-else title="No recent logs" /></BasePanel
      ><BaseButton class="remove" variant="danger" @click="confirm = true"
        >Remove this service</BaseButton
      ></template
    ><ConfirmDialog
      :open="confirm"
      title="Remove service?"
      message="AIOps will stop raising problems for it. Existing telemetry remains until it expires."
      confirm-label="Remove"
      danger
      :busy="busy"
      @cancel="confirm = false"
      @confirm="remove"
    /><Teleport to="body"
      ><div v-if="trace" class="trace-backdrop" @click.self="trace = null">
        <section class="trace">
          <h2>Request trace</h2>
          <div
            v-for="span in trace"
            :key="span.id"
            class="span"
            :class="{ bad: span.error }"
          >
            <b>{{ span.instance || span.service }}</b
            ><span>{{ span.name }}</span
            ><em>{{ milliseconds(span.end - span.start) }}</em>
          </div>
          <BaseButton variant="secondary" @click="trace = null"
            >Close</BaseButton
          >
        </section>
      </div></Teleport
    >
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
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
}
.cols {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-top: 16px;
}
.cols > div {
  display: grid;
  gap: 16px;
  align-content: start;
}
.row {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  border: 0;
  border-bottom: 1px solid var(--color-border-default);
  background: transparent;
  padding: 9px 0;
  text-align: left;
  cursor: pointer;
}
.row.static {
  cursor: default;
}
.row span {
  display: flex;
  min-width: 0;
  flex-direction: column;
}
.row small,
.row em {
  color: var(--color-text-muted);
  font-size: 11px;
  font-style: normal;
}
.logs {
  max-height: 320px;
  overflow: auto;
  font:
    12px/20px ui-monospace,
    monospace;
}
.logs > div {
  display: grid;
  grid-template-columns: 80px 60px 1fr;
  gap: 10px;
}
.logs time {
  color: var(--color-text-dim);
}
.remove {
  margin-top: 16px;
}
.trace-backdrop {
  position: fixed;
  inset: 0;
  z-index: 100;
  display: grid;
  place-items: center;
  background: #17203366;
  padding: 20px;
}
.trace {
  width: min(780px, 100%);
  max-height: 80vh;
  overflow: auto;
  border-radius: 12px;
  background: white;
  padding: 22px;
}
.span {
  display: grid;
  grid-template-columns: 160px 1fr 80px;
  gap: 12px;
  border-bottom: 1px solid var(--color-border-default);
  padding: 9px;
}
.span.bad {
  color: var(--color-status-danger-text);
}
.span em {
  text-align: right;
  font-style: normal;
}
@media (max-width: 800px) {
  .charts,
  .cols {
    grid-template-columns: 1fr;
  }
}
</style>
