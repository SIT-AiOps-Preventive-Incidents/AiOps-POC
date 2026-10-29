<script setup>
// Health as a word with a lit dot - not a badge. "Healthy" in green, "Problem" in red with a soft pulse,
// "Waiting for data" quiet. Optional `value` sits under it (an error rate, a time).
defineProps({ tone: { type: String, default: "neutral" }, label: String, value: String });
</script>
<template>
  <span :class="['hl', `t-${tone}`]">
    <span class="hl__row"><i aria-hidden="true" />{{ label }}</span>
    <span v-if="value" class="hl__v">{{ value }}</span>
  </span>
</template>
<style scoped>
.hl { display: inline-flex; flex-direction: column; align-items: flex-end; gap: 3px; min-width: 96px; text-align: right; }
.hl__row { display: inline-flex; align-items: center; gap: 8px; font-size: var(--fs-sm); font-weight: var(--fw-semibold); white-space: nowrap; color: var(--c-text-2); }
.hl__v { font-size: var(--fs-xs); color: var(--c-text-3); font-variant-numeric: tabular-nums; white-space: nowrap; }
i { width: 8px; height: 8px; border-radius: 50%; background: var(--c-neutral); flex: none; }
.t-ok i { background: var(--c-ok); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-ok) 18%, transparent); }
.t-ok .hl__row { color: var(--c-ok-text); }
.t-bad i { background: var(--c-bad); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-bad) 22%, transparent); animation: hl-pulse 1.8s var(--ease) infinite; }
.t-bad .hl__row { color: var(--c-bad-text); }
.t-warn i { background: var(--c-warn); } .t-warn .hl__row { color: var(--c-warn-text); }
.t-info i { background: var(--c-info); } .t-info .hl__row { color: var(--c-info-text); }
@keyframes hl-pulse { 0%, 100% { box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-bad) 22%, transparent); } 50% { box-shadow: 0 0 0 6px transparent; } }
@media (prefers-reduced-motion: reduce) { .t-bad i { animation: none; } }
</style>
