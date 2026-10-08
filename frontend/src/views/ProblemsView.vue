<script setup>
import ProblemRow from "@/components/domain/ProblemRow.vue";
import { usePolling } from "@/composables/usePolling";
import { useIncidentStore } from "@/stores/incidents";
const store = useIncidentStore();
usePolling(() => store.loadList(), 6000);
const sections = [
  { key: "needsApproval", title: "Needs your approval", empty: "Nothing is waiting for approval" },
  { key: "inProgress", title: "In progress", empty: "No problems are being worked on" },
  { key: "recentlyClosed", title: "Recently closed", empty: "No history yet. Try a demo problem." },
];
</script>
<template>
  <div class="page">
    <UiPageHeader title="Problems" subtitle="The AI investigates every problem. Fixes are dry-run first and only applied after the owner approves." />
    <template v-for="s in sections" :key="s.key">
      <div class="section-label">{{ s.title }} ({{ store[s.key].length }})</div>
      <UiList>
        <ProblemRow v-for="p in store[s.key]" :key="p.id" :incident="p" />
        <UiEmpty v-if="store.loaded && !store[s.key].length">{{ s.empty }}</UiEmpty>
      </UiList>
    </template>
  </div>
</template>
