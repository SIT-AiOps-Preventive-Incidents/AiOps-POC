<script setup>
// A 270-degree ring for one number: the value in the middle, its unit under it, the arc filled to `ratio`.
// Colour follows the tone, so a ring is never decoration - it is green, amber, red or the accent for a measure.
import { computed, useId } from "vue";
const props = defineProps({ ratio: { type: Number, default: 0 }, value: [String, Number], unit: String,
  tone: { type: String, default: "info" }, size: { type: Number, default: 116 }, label: String });
const R = 42, C = 2 * Math.PI * R, ARC = C * 0.75;
const fill = computed(() => Math.max(0, Math.min(1, props.ratio || 0)) * ARC);
const COLOR = { ok: ["var(--c-ok)", "#a9f2cf"], bad: ["var(--c-bad)", "#ffb3b6"], warn: ["var(--c-warn)", "#ffe2a3"],
  info: ["var(--c-gauge)", "var(--c-gauge-hi)"], neutral: ["var(--c-neutral)", "var(--c-neutral)"] };
const gid = useId();
const col = computed(() => COLOR[props.tone] || [props.tone, props.tone]);
</script>
<template>
  <div class="ui-gauge" :style="{ width: `${size}px`, height: `${size}px` }" role="img" :aria-label="label || `${value} ${unit || ''}`">
    <svg viewBox="0 0 100 100">
      <defs><linearGradient :id="gid" x1="0" y1="1" x2="1" y2="0">
        <stop offset="0" :style="{ stopColor: col[0] }" /><stop offset="1" :style="{ stopColor: col[1] }" /></linearGradient></defs>
      <circle cx="50" cy="50" :r="R" class="track" :stroke-dasharray="`${ARC} ${C}`" />
      <circle cx="50" cy="50" :r="R" class="glow" :stroke-dasharray="`${fill} ${C}`" :style="{ stroke: col[0] }" />
      <circle cx="50" cy="50" :r="R" class="arc" :stroke-dasharray="`${fill} ${C}`" :stroke="`url(#${gid})`" />
    </svg>
    <div class="ui-gauge__v"><b>{{ value }}</b><span v-if="unit">{{ unit }}</span></div>
  </div>
</template>
<style scoped>
.ui-gauge { position: relative; flex: none; }
svg { width: 100%; height: 100%; transform: rotate(135deg); }
circle { fill: none; stroke-width: 5; stroke-linecap: round; }
.track { stroke: var(--c-fill-2); }
.arc { transition: stroke-dasharray var(--dur) var(--ease); }
.glow { stroke-width: 10; opacity: 0.18; filter: blur(3px); }
.ui-gauge__v { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; }
.ui-gauge__v b { font-size: 24px; font-weight: var(--fw-bold); letter-spacing: -0.02em; line-height: 1.05; font-variant-numeric: tabular-nums; }
.ui-gauge__v span { font-size: var(--fs-xs); color: var(--c-text-3); margin-top: 2px; }
</style>
