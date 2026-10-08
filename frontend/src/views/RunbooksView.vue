<script setup lang="ts">
import { RouterLink } from "vue-router";
import BaseButton from "@/components/common/BaseButton.vue";
import BasePanel from "@/components/common/BasePanel.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import StatusChip from "@/components/common/StatusChip.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
import { useUiStore } from "@/stores/ui";
const state = useAsyncState(api.runbooks),
  ui = useUiStore();
async function toggle(id: number) {
  try {
    await api.toggleRunbook(id);
    ui.notify("Runbook updated");
    await state.load();
  } catch (e) {
    ui.notify(e instanceof Error ? e.message : "Update failed");
  }
}
</script>
<template>
  <div class="page">
    <PageHeader
      title="Runbook Memory"
      description="Fixes that worked and were rated 4–5 stars. The AI reuses them when the same problem returns."
    /><LoadingState v-if="state.loading && !state.data" /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    />
    <div v-else-if="state.data?.length" class="books">
      <BasePanel v-for="r in state.data" :key="r.id"
        ><template #header
          ><h2>{{ r.title }}</h2>
          <StatusChip :tone="r.enabled ? 'success' : 'neutral'">{{
            r.enabled ? "Enabled" : "Disabled"
          }}</StatusChip></template
        >
        <p>{{ r.root_cause }}</p>
        <ol>
          <li v-for="line in r.runbook" :key="line">{{ line }}</li>
        </ol>
        <div class="meta">
          Used {{ r.uses }}× · rating
          {{ r.score_n ? (r.score_sum / r.score_n).toFixed(1) : "—" }} · from
          <RouterLink class="link" :to="`/problems/${r.source_incident}`"
            >P-{{ r.source_incident }}</RouterLink
          >
        </div>
        <BaseButton
          :variant="r.enabled ? 'ghost' : 'secondary'"
          @click="toggle(r.id)"
          >{{ r.enabled ? "Turn off" : "Turn on" }}</BaseButton
        ></BasePanel
      >
    </div>
    <EmptyState
      v-else
      title="No runbooks yet"
      message="Resolve a problem and rate it 4–5 stars to save the successful fix."
    />
  </div>
</template>
<style scoped>
.books {
  display: grid;
  gap: 12px;
}
.meta {
  margin: 12px 0;
  color: var(--color-text-muted);
  font-size: 12px;
}
</style>
