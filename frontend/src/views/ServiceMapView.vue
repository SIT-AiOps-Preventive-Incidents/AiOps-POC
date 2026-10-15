<script setup>
import { computed } from "vue";
import MapSidePanel from "@/components/domain/MapSidePanel.vue";
import ServiceMapCanvas from "@/components/domain/ServiceMapCanvas.vue";
import TestRequestPanel from "@/components/domain/TestRequestPanel.vue";
import { usePolling } from "@/composables/usePolling";
import { useMapStore } from "@/stores/map";

const map = useMapStore();
usePolling(() => (map.test.phase === "playing" ? null : map.load()), 15000);
// two independent controls, not one long mixed strip: a view (everything / only problems) and, separately,
// which computer to focus on. Both still drive the store's single `filter`, so one wins at a time.
const VIEWS = [{ value: "all", label: "All services" }, { value: "problems", label: "Only problems" }];
const view = computed({
  get: () => (map.filter === "problems" ? "problems" : "all"),
  set: (v) => (map.filter = v),
});
const hosts = computed(() => map.data?.hosts || []);
const focusedHost = computed({
  get: () => (map.filter.startsWith("host:") ? map.filter.slice(5) : ""),
  set: (name) => (map.filter = name ? `host:${name}` : "all"),
});
const busy = computed(() => ["sending", "tracing", "playing"].includes(map.test.phase));
const entry = computed(() => map.data?.nodes.find((n) => n.entry_url));
</script>
<template>
  <div class="page page--wide">
    <UiPageHeader title="Service map" subtitle="Every hop a request takes, left to right. Computers you connect show what runs on them below.">
      <UiButton icon="play" :loading="busy" :disabled="!entry" @click="map.runTest()">{{ busy ? "Running test…" : "Send test request" }}</UiButton>
    </UiPageHeader>
    <div class="filter">
      <UiSegmented v-model="view" :options="VIEWS" label="View" />
      <label v-if="hosts.length" class="focus">
        <span class="muted small">Focus a computer</span>
        <select v-model="focusedHost">
          <option value="">All computers</option>
          <option v-for="h in hosts" :key="h.name" :value="h.name">{{ h.name }}</option>
        </select>
      </label>
    </div>
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
.filter { display: flex; align-items: center; gap: 20px; flex-wrap: wrap; margin-bottom: 14px; }
.focus { display: flex; align-items: center; gap: 8px; }
.focus select { font: inherit; font-size: var(--fs-sm); padding: 6px 10px; border: 1px solid var(--c-border); border-radius: var(--radius-md);
  background: var(--c-surface); color: var(--c-text); cursor: pointer; }
.focus select:hover { border-color: var(--c-primary); }
.layout { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; align-items: start; }
.layout.with-side { grid-template-columns: minmax(0, 1fr) 340px; }
@media (max-width: 1080px) { .layout.with-side { grid-template-columns: 1fr; } }
</style>
