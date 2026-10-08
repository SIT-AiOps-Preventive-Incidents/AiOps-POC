<script setup lang="ts">
import BasePanel from "@/components/common/BasePanel.vue";
import EmptyState from "@/components/common/EmptyState.vue";
import ErrorState from "@/components/common/ErrorState.vue";
import LoadingState from "@/components/common/LoadingState.vue";
import PageHeader from "@/components/common/PageHeader.vue";
import { useAsyncState } from "@/composables/useAsyncState";
import { api } from "@/services/api";
import { ago } from "@/utils/format";
const state = useAsyncState(api.deployments, 15000);
</script>
<template>
  <div class="page">
    <PageHeader
      title="Deployments"
      description="Versions and commits reported by CI. The AI uses them to link a problem to the change behind it."
    /><LoadingState v-if="state.loading && !state.data" /><ErrorState
      v-else-if="state.error && !state.data"
      :message="state.error"
      @retry="state.load()"
    /><BasePanel v-else title="Deployment history" flush
      ><div v-if="state.data?.length" class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Service</th>
              <th>Version</th>
              <th>Commit</th>
              <th>Author</th>
              <th>Message</th>
              <th>When</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in state.data" :key="d.id">
              <td>{{ d.service }}</td>
              <td>v{{ d.version }}</td>
              <td>
                <code>{{ d.commit_hash }}</code>
              </td>
              <td>{{ d.author }}</td>
              <td>{{ d.message }}</td>
              <td>{{ ago(d.ts) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <EmptyState v-else title="No deployments reported"
    /></BasePanel>
  </div>
</template>
