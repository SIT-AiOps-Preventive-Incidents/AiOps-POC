<script setup>
import ProblemRow from "@/components/domain/ProblemRow.vue";
import { usePolling } from "@/composables/usePolling";
import { useIncidentStore } from "@/stores/incidents";
const store = useIncidentStore();
usePolling(() => store.loadList(), 6000);
const sections = [
  { key: "needsApproval", title: "Waiting for your approval", empty: "Nothing is waiting for you" },
  { key: "inProgress", title: "In progress", empty: "No incidents are being worked on" },
  { key: "recentlyClosed", title: "Recently closed", empty: "No history yet. Run a demo scenario to see one." },
];
</script>
<template>
  <div class="page">
    <UiPageHeader eyebrow="Respond" title="Incidents" subtitle="The AI investigates each incident and tests a fix in a dry run. A fix is applied only after its owner approves it." />
    <UiSkeletonPage v-if="!store.loaded" :header="false" :rows="6" />
    <template v-for="s in sections" v-else :key="s.key">
      <div class="section-label">{{ s.title }} ({{ store[s.key].length }})</div>
      <UiList>
        <ProblemRow v-for="p in store[s.key]" :key="p.id" :incident="p" />
        <UiEmpty v-if="store.loaded && !store[s.key].length">{{ s.empty }}</UiEmpty>
      </UiList>
    </template>
  </div>
</template>
