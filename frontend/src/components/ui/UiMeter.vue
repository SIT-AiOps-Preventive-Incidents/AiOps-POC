<script setup>
import { computed } from "vue";
const props = defineProps({ label: String, value: Number, warn: { type: Number, default: 70 }, crit: { type: Number, default: 90 },
  max: { type: Number, default: 100 }, suffix: { type: String, default: "%" } });
const color = computed(() => (props.value == null ? "var(--c-neutral)" : props.value >= props.crit ? "var(--c-bad)"
  : props.value >= props.warn ? "var(--c-warn)" : "var(--c-ok)"));
</script>
<template>
  <div class="ui-meter">
    <span class="muted">{{ label }}</span>
    <div class="ui-meter__bar" role="meter" :aria-valuenow="value" :aria-valuemax="max" :aria-label="label">
      <div :style="{ width: `${Math.min(((value || 0) / max) * 100, 100)}%`, background: color }" />
    </div>
    <span class="ui-meter__v">{{ value == null ? "-" : `${Math.round(value)}${suffix}` }}</span>
  </div>
</template>
<style scoped>
.ui-meter { display: grid; grid-template-columns: 64px minmax(0, 1fr) 46px; gap: 8px; align-items: center; font-size: var(--fs-sm); margin-top: 6px; }
.ui-meter__bar { height: 6px; background: var(--c-fill-2); border-radius: 3px; overflow: hidden; }
.ui-meter__bar div { height: 100%; border-radius: 3px; transition: width var(--dur) var(--ease); }
.ui-meter__v { text-align: right; color: var(--c-text-2); font-variant-numeric: tabular-nums; }
</style>
