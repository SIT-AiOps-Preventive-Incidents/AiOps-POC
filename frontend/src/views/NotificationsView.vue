<script setup>
import { ref } from "vue";
import { usePageFacts } from "@/composables/usePageFacts";
import { usePolling } from "@/composables/usePolling";
import { api } from "@/lib/api";
import { ago } from "@/lib/format";
const rows = ref(null);
usePolling(async () => { rows.value = await api.notifications.list(); }, 10000);
usePageFacts(() => ({ recent_notifications: rows.value?.length }));
</script>
<template>
  <div class="page">
    <UiPageHeader eyebrow="Setup" title="Notifications" subtitle="Cards sent to Microsoft Teams. Add the Teams link in Settings." />
    <UiList>
      <UiListRow v-for="n in rows" :key="n.id" :to="n.incident_id ? `/problems/${n.incident_id}` : '/settings'"
                 :title="`${n.event.replace(/_/g, ' ')}${n.incident_id ? ` · P-${n.incident_id}` : ''}`" :subtitle="n.status">
        <template #leading><UiAppTile logo="teams" :status="n.status.startsWith('sent') ? 'ok' : undefined" /></template>
        <template #accessory>{{ ago(n.ts) }}</template>
      </UiListRow>
      <UiEmpty v-if="rows && !rows.length">Nothing sent yet</UiEmpty>
    </UiList>
  </div>
</template>
