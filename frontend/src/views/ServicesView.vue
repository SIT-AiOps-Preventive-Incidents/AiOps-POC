<script setup lang="ts">
import { ref } from "vue";
import { RouterLink } from "vue-router";
import BaseButton from "@/components/common/BaseButton.vue";
import BaseInput from "@/components/common/BaseInput.vue";
import BasePanel from "@/components/common/BasePanel.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
import { useUiStore } from "@/stores/ui";
import { milliseconds, number, percent } from "@/utils/format";
const ui = useUiStore();
const state = useAsyncState(async () => {
  const [apps, discovery] = await Promise.all([
    api.apps(),
    api
      .discover()
      .catch(() => ({ services: [], hosts: [], otlp_endpoint: "", api: "" })),
  ]);
  return { apps, discovery };
}, 10000);
const dialog = ref<HTMLDialogElement>();
const selected = ref("");
const owner = ref(localStorage.getItem("lastOwner") || "");
const busy = ref(false);
function openAdd(service = "") {
  selected.value = service;
  dialog.value?.showModal();
}
async function add() {
  if (!selected.value.trim()) return ui.notify("Enter a service name");
  busy.value = true;
  try {
    await api.createApp({
      service_name: selected.value.trim().toLowerCase().replace(/\s+/g, "-"),
      owner: owner.value.trim() || "unassigned",
    });
    localStorage.setItem("lastOwner", owner.value);
    dialog.value?.close();
    ui.notify("Service connected");
    await state.load();
  } catch (error) {
    ui.notify(
      error instanceof Error ? error.message : "Could not connect service",
    );
  } finally {
    busy.value = false;
  }
}
</script>
<template>
  <div class="page">
    <PageHeader
      title="Services"
      description="Applications sending OpenTelemetry traces and logs. Metrics are tagged with version and commit."
      ><RouterLink to="/connect/service"
        ><BaseButton>+ Connect app</BaseButton></RouterLink
      ></PageHeader
    ><LoadingState v-if="state.loading && !state.data" /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    /><template v-else-if="state.data"
      ><BasePanel
        v-if="state.data.discovery.services.length"
        title="Found, not added yet"
        ><div
          class="discovered"
          v-for="service in state.data.discovery.services"
          :key="service.service_name"
        >
          <span
            ><strong>{{ service.service_name }}</strong
            ><small
              >Already sending telemetry ·
              {{ number(service.rps) }} req/s</small
            ></span
          ><BaseButton
            variant="secondary"
            @click="openAdd(service.service_name)"
            >Add</BaseButton
          >
        </div></BasePanel
      ><BasePanel title="Connected services" flush
        ><div v-if="state.data.apps.length" class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Service</th>
                <th>Team</th>
                <th>Version / Commit</th>
                <th>Req/s</th>
                <th>Failure rate</th>
                <th>P95</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="app in state.data.apps" :key="app.id">
                <td>
                  <RouterLink
                    class="link"
                    :to="`/services/${app.service_name}`"
                    >{{ app.name }}</RouterLink
                  >
                </td>
                <td>{{ app.owner || app.team || "—" }}</td>
                <td>
                  {{
                    app.version ? `v${app.version} · ${app.commit || ""}` : "—"
                  }}
                </td>
                <td>{{ number(app.rps) }}</td>
                <td :class="(app.error_rate || 0) > 0.05 ? 'danger-text' : ''">
                  {{ percent(app.error_rate) }}
                </td>
                <td>{{ milliseconds(app.p95_ms) }}</td>
                <td :class="app.problem_id ? 'danger-text' : 'success-text'">
                  {{ app.problem_id ? `P-${app.problem_id}` : app.status }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <EmptyState v-else title="No services connected"
          ><RouterLink class="link" to="/connect/service"
            >Connect your first service</RouterLink
          ></EmptyState
        ></BasePanel
      ></template
    >
    <dialog ref="dialog" class="modal">
      <form method="dialog" @submit.prevent="add">
        <h2>Add service</h2>
        <BaseInput v-model="selected" label="Service name" required /><BaseInput
          v-model="owner"
          label="Owner team"
          placeholder="team-orders"
        />
        <div class="actions">
          <BaseButton variant="secondary" @click="dialog?.close()"
            >Cancel</BaseButton
          ><BaseButton type="submit" :disabled="busy">{{
            busy ? "Adding…" : "Add service"
          }}</BaseButton>
        </div>
      </form>
    </dialog>
  </div>
</template>
<style scoped>
.page > :deep(.panel) + :deep(.panel) {
  margin-top: 16px;
}
.discovered {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--color-border-default);
}
.discovered span {
  display: flex;
  flex-direction: column;
}
.discovered small {
  color: var(--color-text-muted);
}
.modal {
  width: min(460px, calc(100% - 32px));
  border: 0;
  border-radius: var(--radius-lg);
  padding: 22px;
  box-shadow: var(--shadow-dialog);
}
.modal::backdrop {
  background: rgb(23 32 51 / 40%);
}
.modal h2 {
  margin-top: 0;
}
.modal :deep(.input) + :deep(.input) {
  margin-top: 12px;
}
.actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-top: 20px;
}
</style>
