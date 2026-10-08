<script setup>
import { STEP_KIND } from "@/lib/vocab";
defineProps({ steps: { type: Array, default: () => [] } });
const meta = (s) => STEP_KIND[s.kind] || STEP_KIND.info;
const payload = (s) => {
  const d = s.data || {};
  if (d.output !== undefined) return d.output;
  if (d.checks) return { checks: d.checks, changes: d.changes, impact: d.impact };
  if (d.facts) return { facts: d.facts, candidates: d.candidates };
  return null;
};
</script>
<template>
  <div class="tl">
    <div v-for="s in steps" :key="s.id || s.seq" class="tl__row">
      <span class="tl__ic" :style="{ background: meta(s).color }"><UiIcon :name="meta(s).icon" filled :size="14" /></span>
      <div class="tl__body">
        <div>{{ s.kind === "tool" ? `${s.title}()` : s.title }}</div>
        <div v-if="s.detail" class="small muted">{{ s.detail }}</div>
        <div v-if="s.data?.rejected" class="small dim">AI wrote: "{{ s.data.rejected }}"</div>
        <UiDisclosure v-if="payload(s)" :card="false" title="details"><pre>{{ JSON.stringify(payload(s), null, 2) }}</pre></UiDisclosure>
      </div>
      <span class="small dim">{{ s.duration_ms != null ? (s.duration_ms / 1000).toFixed(1) + " s" : "" }}</span>
    </div>
    <UiEmpty v-if="!steps.length">Not started</UiEmpty>
  </div>
</template>
<style scoped>
.tl__row { display: flex; gap: 10px; align-items: flex-start; padding: 8px 0; border-top: 0.5px solid var(--c-separator); font-size: 14px; }
.tl__row:first-child { border-top: 0; }
.tl__ic { width: 24px; height: 24px; border-radius: 6px; display: grid; place-items: center; color: #fff; flex: none; }
.tl__body { flex: 1; min-width: 0; }
pre { background: var(--c-fill); border-radius: 10px; padding: 10px 12px; font: 12px/1.5 var(--font-mono); white-space: pre-wrap; word-break: break-word; margin: 8px 0 0; max-height: 320px; overflow: auto; }
</style>
