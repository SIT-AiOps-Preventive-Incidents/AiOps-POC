<script setup>
import { computed } from "vue";
import { ms } from "@/lib/format";
const props = defineProps({ spans: { type: Array, default: () => [] } });
const rows = computed(() => {
  const s = props.spans;
  if (!s.length) return [];
  const t0 = Math.min(...s.map((x) => x.start)), t1 = Math.max(...s.map((x) => x.end)), span = t1 - t0 || 1;
  const byId = Object.fromEntries(s.map((x) => [x.id, x])), depth = {};
  const d = (x) => depth[x.id] ?? (depth[x.id] = byId[x.parent] ? d(byId[x.parent]) + 1 : 0);
  return s.map((x) => ({ ...x, depth: d(x), left: ((x.start - t0) / span) * 100, width: Math.max(((x.end - x.start) / span) * 100, 0.6) }));
});
</script>
<template>
  <div class="wf">
    <div v-for="r in rows" :key="r.id" class="wf__row">
      <div class="wf__name" :class="{ bad: r.error }" :style="{ paddingLeft: `${r.depth * 12}px` }"><b>{{ r.instance || r.service }}</b> <span class="muted">{{ r.name }}</span></div>
      <div class="wf__track"><div class="wf__bar" :class="{ err: r.error }" :style="{ left: `${r.left}%`, width: `${r.width}%` }" /></div>
      <div class="wf__ms">{{ ms(r.end - r.start) }}</div>
      <div v-if="r.error && r.status_msg" class="wf__err bad" :style="{ paddingLeft: `${r.depth * 12 + 4}px` }">{{ r.status_msg }}</div>
    </div>
  </div>
</template>
<style scoped>
.wf__row { display: grid; grid-template-columns: 220px minmax(0, 1fr) 64px; gap: 8px; align-items: center; font-size: 13px; padding: 4px 0; border-bottom: 0.5px solid var(--c-separator); }
.wf__name { min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.wf__track { position: relative; height: 16px; }
.wf__bar { position: absolute; height: 10px; top: 3px; border-radius: 3px; background: var(--c-chart-1); }
.wf__bar.err { background: var(--c-chart-2); }
.wf__ms { text-align: right; color: var(--c-text-2); font-variant-numeric: tabular-nums; }
.wf__err { grid-column: 1 / -1; font-size: 12px; }
@media (max-width: 760px) { .wf__row { grid-template-columns: 120px minmax(0, 1fr) 56px; } }
</style>
