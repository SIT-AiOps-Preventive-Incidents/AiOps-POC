<script setup>
// Small area chart: faint top grid line, gradient fill, current value in the header. points: [[epochSec, value], ...]
import { computed, useId } from "vue";
import { clock } from "@/lib/format";
const props = defineProps({ title: String, points: { type: Array, default: () => [] }, color: { type: String, default: "var(--c-chart-1)" },
  format: { type: Function, default: (v) => Number(v).toFixed(2) }, height: { type: Number, default: 96 } });
const gid = useId();
const W = 600;
const g = computed(() => {
  const pts = props.points.filter((p) => p[1] != null);
  if (pts.length < 2) return null;
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), peak = Math.max(...ys), ymax = peak * 1.15 || 1, h = props.height;
  const X = (x) => ((x - x0) / (x1 - x0 || 1)) * W, Y = (y) => h - 2 - (y / ymax) * (h - 10);
  return { line: pts.map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" "), peakY: Y(peak), peak, x0, x1, last: ys[ys.length - 1] };
});
</script>
<template>
  <div class="chart">
    <div class="chart__head"><h3>{{ title }}</h3><span v-if="g" class="chart__v">{{ format(g.last) }}</span></div>
    <svg v-if="g" :viewBox="`0 0 ${W} ${height}`" preserveAspectRatio="none" :style="{ height: `${height}px` }" role="img" :aria-label="`${title} over the last hour`">
      <defs><linearGradient :id="gid" x1="0" x2="0" y1="0" y2="1"><stop offset="0" :style="{ stopColor: color, stopOpacity: 0.22 }" /><stop offset="1" :style="{ stopColor: color, stopOpacity: 0 }" /></linearGradient></defs>
      <line x1="0" :x2="W" :y1="g.peakY" :y2="g.peakY" style="stroke: var(--c-separator)" stroke-dasharray="3 4" />
      <polygon :points="`0,${height} ${g.line} ${W},${height}`" :fill="`url(#${gid})`" />
      <polyline :points="g.line" fill="none" :style="{ stroke: color }" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" />
    </svg>
    <div v-if="g" class="chart__axis"><span>{{ clock(g.x0) }}</span><span>peak {{ format(g.peak) }}</span><span>{{ clock(g.x1) }}</span></div>
    <div v-else class="chart__empty">Waiting for data</div>
  </div>
</template>
<style scoped>
.chart { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 16px 18px; min-width: 0; }
.chart__head { display: flex; justify-content: space-between; align-items: baseline; }
.chart__head h3 { font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-text-2); text-transform: uppercase; letter-spacing: 0.03em; }
.chart__v { font-size: 22px; font-weight: var(--fw-bold); font-variant-numeric: tabular-nums; letter-spacing: -0.02em; }
svg { width: 100%; display: block; margin-top: 6px; }
.chart__axis { display: flex; justify-content: space-between; font-size: 12px; color: var(--c-text-3); }
.chart__empty { padding: 26px 0; text-align: center; color: var(--c-text-2); font-size: 14px; }
</style>
