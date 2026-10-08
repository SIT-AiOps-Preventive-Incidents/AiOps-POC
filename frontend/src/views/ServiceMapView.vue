<script setup>
import { computed } from "vue";
import MapSidePanel from "@/components/domain/MapSidePanel.vue";
import ServiceMapCanvas from "@/components/domain/ServiceMapCanvas.vue";
import TestRequestPanel from "@/components/domain/TestRequestPanel.vue";
import { usePolling } from "@/composables/usePolling";
import { useMapStore } from "@/stores/map";

const map = useMapStore();
usePolling(() => (map.test.phase === "playing" ? null : map.load()), 15000);
const filters = computed(() => [
  { value: "all", label: "All" }, { value: "problems", label: "Problems only" },
  ...(map.data?.hosts || []).map((h) => ({ value: `host:${h.name}`, label: h.name })),
]);
const busy = computed(() => ["sending", "tracing", "playing"].includes(map.test.phase));
const entry = computed(() => map.data?.nodes.find((n) => n.entry_url));
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader title="Service Map" subtitle="Every hop a request takes, left to right. Computers you connect show what runs on them below.">
      <UiButton icon="play" :loading="busy" :disabled="!entry" @click="map.runTest()">{{ busy ? "Running test..." : "Send test request" }}</UiButton>
    </UiPageHeader>
    <UiSegmented v-model="map.filter" :options="filters" label="Filter the map" class="filter" />
    <div :class="['layout', { 'with-side': map.selected || map.test.phase !== 'idle' }]">
      <ServiceMapCanvas @select="map.select" />
      <div v-if="map.selected || map.test.phase !== 'idle'" class="stack">
        <TestRequestPanel />
        <MapSidePanel />
      </div>
    </div>
    <p class="small dim mt-2">Solid lines come from traces; dashed lines are connections an agent saw on a computer. Red means more than 5% of requests failed.
      <template v-if="entry"> The test request enters at <b>{{ entry.id }}</b> ({{ entry.entry_url }}).</template></p>
  </div>
</template>
<style scoped>
.filter { margin-bottom: 14px; }
.layout { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-items: start; }
.layout.with-side { grid-template-columns: minmax(0, 1fr) 340px; }
@media (max-width: 1080px) { .layout.with-side { grid-template-columns: 1fr; } }
</style>
