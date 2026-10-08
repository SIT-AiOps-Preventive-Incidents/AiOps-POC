<script setup>
import { ref } from "vue";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
const rbs = ref([]);
const { refresh } = usePolling(async () => { rbs.value = await api.runbooks.list(); }, 30000);
async function toggle(r) { await api.runbooks.setEnabled(r.id, !r.enabled); refresh(); }
</script>
<template>
  <div class="page">
    <UiPageHeader title="Runbooks" subtitle="Fixes that worked and were rated 4-5 stars. When the same problem comes back, the AI reuses them instead of starting over." />
    <UiList>
      <UiListRow v-for="r in rbs" :key="r.id" :title="`RB-${r.id} ${r.title}`" :detail="r.root_cause"
                 :subtitle="`Used ${r.uses}× · rating ${r.avg_score ?? '-'} (${r.ratings}) · ${(r.steps || []).length} steps`">
        <template #leading><UiAppTile icon="book" :color="r.enabled ? 'var(--c-chart-5)' : 'var(--c-neutral)'" /></template>
        <template #accessory><router-link v-if="r.source_incident_id" :to="`/problems/${r.source_incident_id}`" class="small">P-{{ r.source_incident_id }}</router-link>
          <UiSwitch :model-value="r.enabled" :label="`Use RB-${r.id}`" @update:model-value="toggle(r)" /></template>
      </UiListRow>
      <UiEmpty v-if="!rbs.length">No runbooks yet. Resolve a problem and rate it 4-5 stars.</UiEmpty>
    </UiList>
  </div>
</template>
