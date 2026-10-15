<script setup>
// Determinate progress: the ring fills as steps finish and closes only when the work is done (a checkmark).
// Unlike UiSpinner it never spins - the amount drawn is the amount done.
import { computed } from "vue";
const props = defineProps({ value: { type: Number, default: 0 }, state: { type: String, default: "running" }, size: { type: Number, default: 88 } });
const R = 42, C = 2 * Math.PI * R;
const dash = computed(() => `${(Math.max(0, Math.min(1, props.value)) * C).toFixed(1)} ${C.toFixed(1)}`);
</script>
<template>
  <div :class="['ui-ring', `ui-ring--${state}`]" :style="{ width: `${size}px`, height: `${size}px` }"
       role="progressbar" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="Math.round(value * 100)">
    <svg viewBox="0 0 100 100" :width="size" :height="size">
      <circle cx="50" cy="50" :r="R" class="track" />
      <circle cx="50" cy="50" :r="R" class="bar" :stroke-dasharray="dash" transform="rotate(-90 50 50)" />
      <path v-if="state === 'done'" d="M33 51l11 11 23-25" class="mark" />
      <path v-else-if="state === 'failed'" d="M38 38l24 24M62 38L38 62" class="mark" />
    </svg>
    <span v-if="state !== 'done' && state !== 'failed'" class="pct">{{ Math.round(value * 100) }}%</span>
  </div>
</template>
<style scoped>
.ui-ring { position: relative; display: inline-grid; place-items: center; flex: none; }
svg { position: absolute; inset: 0; }
.track { fill: none; stroke: var(--c-fill-2); stroke-width: 8; }
.bar { fill: none; stroke: var(--c-primary); stroke-width: 8; stroke-linecap: round; transition: stroke-dasharray 0.6s ease; }
.ui-ring--done .bar { stroke: var(--c-ok); }
.ui-ring--failed .bar { stroke: var(--c-bad); }
.mark { fill: none; stroke-width: 8; stroke-linecap: round; stroke-linejoin: round; }
.ui-ring--done .mark { stroke: var(--c-ok); }
.ui-ring--failed .mark { stroke: var(--c-bad); }
.pct { font-weight: 700; font-size: 17px; font-variant-numeric: tabular-nums; }
@media (prefers-reduced-motion: reduce) { .bar { transition: none; } }
</style>
