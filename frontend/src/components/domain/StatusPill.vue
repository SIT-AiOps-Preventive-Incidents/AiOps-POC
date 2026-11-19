<script setup>
// Where the incident is on its way to a fix: a five-step track (detected, AI, your call, fixing, fixed) and a short
// label. Your turn is the only step that lights in the action colour, so a list of them scans in one look.
import { computed } from "vue";
import { STEPS, stageOf } from "@/lib/stage";
const props = defineProps({ status: String });
const s = computed(() => stageOf(props.status));
</script>
<template>
  <span :class="['stage', `t-${s.tone}`]" :aria-label="`Status: ${s.label}`">
    <span class="stage__label">{{ s.label }}</span>
    <span class="stage__track" aria-hidden="true">
      <i v-for="k in STEPS" :key="k" :class="{ done: k - 1 < s.step, now: k - 1 === s.step }" />
    </span>
  </span>
</template>
<style scoped>
.stage { display: inline-flex; flex-direction: column; gap: 6px; min-width: 104px; }
.stage__label { font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-text-2); white-space: nowrap; }
.stage__track { display: grid; grid-template-columns: repeat(5, 1fr); gap: 3px; }
.stage__track i { height: 4px; border-radius: 2px; background: var(--c-fill-2); }
.stage__track i.done { background: color-mix(in srgb, var(--c-text) 45%, transparent); }
.t-action .stage__label { color: var(--c-action-text); }
.t-action .stage__track i.now { background: var(--c-action); box-shadow: 0 0 8px color-mix(in srgb, var(--c-action) 60%, transparent); }
.t-info .stage__label { color: var(--c-info-text); } .t-info .stage__track i.now { background: var(--c-info); }
.t-ok .stage__label { color: var(--c-ok-text); } .t-ok .stage__track i, .t-ok .stage__track i.done { background: var(--c-ok); }
.t-bad .stage__label { color: var(--c-bad-text); } .t-bad .stage__track i.now { background: var(--c-bad); }
.t-neutral .stage__track i.now { background: var(--c-text-3); }
</style>
