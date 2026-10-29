<script setup>
// A 270-degree ring for one number: the value in the middle, its unit under it, the arc filled to `ratio`.
// Colour follows the tone, so a ring is never decoration - it is green, amber, red or the accent for a measure.
import { computed } from "vue";
const props = defineProps({ ratio: { type: Number, default: 0 }, value: [String, Number], unit: String,
  tone: { type: String, default: "info" }, size: { type: Number, default: 116 }, label: String });
const R = 42, C = 2 * Math.PI * R, ARC = C * 0.75;
const fill = computed(() => Math.max(0, Math.min(1, props.ratio || 0)) * ARC);
const COLOR = { ok: "var(--c-ok)", bad: "var(--c-bad)", warn: "var(--c-warn)", info: "var(--c-primary)", neutral: "var(--c-neutral)" };
</script>
<template>
  <div class="ui-gauge" :style="{ width: `${size}px`, height: `${size}px` }" role="img" :aria-label="label || `${value} ${unit || ''}`">
    <svg viewBox="0 0 100 100">
      <circle cx="50" cy="50" :r="R" class="track" :stroke-dasharray="`${ARC} ${C}`" />
      <circle cx="50" cy="50" :r="R" class="arc" :stroke-dasharray="`${fill} ${C}`" :style="{ stroke: COLOR[tone] || tone }" />
    </svg>
    <div class="ui-gauge__v"><b>{{ value }}</b><span v-if="unit">{{ unit }}</span></div>
  </div>
</template>
<style scoped>
.ui-gauge { position: relative; flex: none; }
svg { width: 100%; height: 100%; transform: rotate(135deg); }
circle { fill: none; stroke-width: 6; stroke-linecap: round; }
.track { stroke: var(--c-fill-2); }
.arc { transition: stroke-dasharray var(--dur) var(--ease); }
.ui-gauge__v { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.ui-gauge__v b { font-size: 24px; font-weight: var(--fw-bold); letter-spacing: -0.02em; line-height: 1.05; font-variant-numeric: tabular-nums; }
.ui-gauge__v span { font-size: var(--fs-xs); color: var(--c-text-3); margin-top: 2px; }
</style>
