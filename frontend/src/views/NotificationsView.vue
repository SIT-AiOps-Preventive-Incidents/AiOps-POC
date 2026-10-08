<script setup lang="ts">
import { RouterLink } from "vue-router";
import AppIcon from "@/components/common/AppIcon.vue";
import BasePanel from "@/components/common/BasePanel.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
import { ago, titleCase } from "@/utils/format";
const state = useAsyncState(api.notifications, 10000);
</script>
<template>
  <div class="page">
    <PageHeader
      title="Notifications"
      description="Messages sent to Microsoft Teams. Configure the destination in Settings."
    /><LoadingState v-if="state.loading && !state.data" /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    /><BasePanel v-else
      ><div v-if="state.data?.length" class="notifications">
        <RouterLink
          v-for="n in state.data"
          :key="n.id"
          :to="n.incident_id ? `/problems/${n.incident_id}` : '/settings'"
          ><AppIcon name="notifications" /><span
            ><b
              >{{ titleCase(n.event)
              }}<template v-if="n.incident_id">
                · P-{{ n.incident_id }}</template
              ></b
            ><small>{{ n.status }}</small></span
          ><em>{{ ago(n.ts) }}</em></RouterLink
        >
      </div>
      <EmptyState v-else title="Nothing sent yet"
    /></BasePanel>
  </div>
</template>
<style scoped>
.notifications a {
  display: grid;
  grid-template-columns: 32px 1fr auto;
  align-items: center;
  gap: 12px;
  border-bottom: 1px solid var(--color-border-default);
  padding: 11px;
}
.notifications a:hover {
  background: var(--color-status-info-bg);
}
.notifications span {
  display: flex;
  flex-direction: column;
}
.notifications small,
.notifications em {
  color: var(--color-text-muted);
  font-size: 12px;
  font-style: normal;
}
</style>
