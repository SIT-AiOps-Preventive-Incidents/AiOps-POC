<script setup>
// "Utilization 87%": a label and value on one line, a thin bar under them. Used on every resource card.
defineProps({ label: String, value: [String, Number], ratio: { type: Number, default: 0 }, tone: String });
</script>
<template>
  <div class="ui-bar">
    <div class="ui-bar__row"><span>{{ label }}</span><b>{{ value }}</b></div>
    <div class="ui-bar__track" role="meter" :aria-label="label" :aria-valuenow="Math.round((ratio || 0) * 100)" aria-valuemin="0" aria-valuemax="100">
      <div :class="['ui-bar__fill', tone && `t-${tone}`]" :style="{ width: `${Math.max(0, Math.min(1, ratio || 0)) * 100}%` }" />
    </div>
  </div>
</template>
<style scoped>
.ui-bar__row { display: flex; justify-content: space-between; align-items: baseline; font-size: var(--fs-md); color: var(--c-text-2); margin-bottom: 9px; }
.ui-bar__row b { color: var(--c-text); font-weight: var(--fw-semibold); font-variant-numeric: tabular-nums; }
.ui-bar__track { height: 4px; border-radius: 2px; background: var(--c-fill-2); overflow: hidden; }
.ui-bar__fill { height: 100%; border-radius: 2px; background: var(--c-text); transition: width var(--dur) var(--ease); }
.t-ok { background: var(--c-ok); } .t-bad { background: var(--c-bad); } .t-warn { background: var(--c-warn); } .t-info { background: var(--c-primary); }
</style>
