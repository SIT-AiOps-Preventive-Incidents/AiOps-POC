<script setup>
// Small area chart: current value in the header, gradient fill, and - when `normal` is given - the range that is
// normal for this host or service at this time of day, shaded behind the line, with a plain verdict.
// points: [[epochSec, value], ...]   normal: { normal_low, normal_high, state, learned_from, days } (from the API)
import { computed, useId } from "vue";
import { clock } from "@/lib/format";
const props = defineProps({ title: String, points: { type: Array, default: () => [] }, color: { type: String, default: "var(--c-chart-1)" },
  format: { type: Function, default: (v) => Number(v).toFixed(2) }, height: { type: Number, default: 96 }, normal: Object });
const gid = useId();
const W = 600;
const band = computed(() => (props.normal && props.normal.normal_low != null ? props.normal : null));
const g = computed(() => {
  const pts = props.points.filter((p) => p[1] != null);
  if (pts.length < 2) return null;
  const xs = pts.map((p) => p[0]), ys = pts.map((p) => p[1]);
  const top = Math.max(...ys, band.value ? band.value.normal_high : 0);
  const x0 = Math.min(...xs), x1 = Math.max(...xs), peak = Math.max(...ys), ymax = top * 1.15 || 1, h = props.height;
  const X = (x) => ((x - x0) / (x1 - x0 || 1)) * W, Y = (y) => h - 2 - (y / ymax) * (h - 10);
  const b = band.value ? { y: Y(band.value.normal_high), h: Math.max(2, Y(band.value.normal_low) - Y(band.value.normal_high)) } : null;
  return { line: pts.map((p) => `${X(p[0]).toFixed(1)},${Y(p[1]).toFixed(1)}`).join(" "), peakY: Y(peak), peak, x0, x1, last: ys[ys.length - 1], b };
});
const verdict = computed(() => {
  const n = props.normal;
  if (!n) return null;
  if (n.state === "learning" || n.normal_low == null) return { tone: "neutral", text: "Learning what is normal" };
  if (n.state === "high") return { tone: "bad", text: n.reason === "safety" ? "Over the safety limit" : "Above normal" };
  if (n.state === "low") return { tone: "bad", text: "Below normal" };
  // inside the tolerance, so no incident - but worth seeing before it becomes one
  if (n.value != null && n.value > n.normal_high) return { tone: "warn", text: "Higher than usual" };
  if (n.value != null && n.value < n.normal_low) return { tone: "warn", text: "Lower than usual" };
  return { tone: "ok", text: "Normal" };
});
const learnedFrom = computed(() => (props.normal?.learned_from === "same_hour"
  ? `this time of day, last ${props.normal.days} days` : "the last 24 hours"));
</script>
<template>
  <div class="chart">
    <div class="chart__head"><h3>{{ title }}</h3><span v-if="g" class="chart__v">{{ format(g.last) }}</span></div>
    <svg v-if="g" :viewBox="`0 0 ${W} ${height}`" preserveAspectRatio="none" :style="{ height: `${height}px` }" role="img" :aria-label="`${title} over the last hour`">
      <defs><linearGradient :id="gid" x1="0" x2="0" y1="0" y2="1"><stop offset="0" :style="{ stopColor: color, stopOpacity: 0.22 }" /><stop offset="1" :style="{ stopColor: color, stopOpacity: 0 }" /></linearGradient></defs>
      <rect v-if="g.b" x="0" :y="g.b.y" :width="W" :height="g.b.h" class="band" />
      <line x1="0" :x2="W" :y1="g.peakY" :y2="g.peakY" style="stroke: var(--c-separator)" stroke-dasharray="3 4" />
      <polygon :points="`0,${height} ${g.line} ${W},${height}`" :fill="`url(#${gid})`" />
      <polyline :points="g.line" fill="none" :style="{ stroke: color }" stroke-width="2" vector-effect="non-scaling-stroke" stroke-linejoin="round" />
    </svg>
    <div v-if="g" class="chart__axis"><span>{{ clock(g.x0) }}</span><span>peak {{ format(g.peak) }}</span><span>{{ clock(g.x1) }}</span></div>
    <div v-else class="chart__empty">Waiting for data</div>
    <div v-if="verdict" class="chart__normal">
      <UiPill :tone="verdict.tone">{{ verdict.text }}</UiPill>
      <span v-if="band" :title="`Learned from ${learnedFrom}`">Usually {{ format(band.normal_low) === format(band.normal_high)
        ? `about ${format(band.normal_low)}` : `${format(band.normal_low)} to ${format(band.normal_high)}` }}</span>
    </div>
  </div>
</template>
<style scoped>
.chart { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); padding: 14px 16px; min-width: 0; }
.chart__head { display: flex; justify-content: space-between; align-items: baseline; }
.chart__head h3 { font-size: var(--fs-sm); font-weight: var(--fw-semibold); color: var(--c-text-2); }
.chart__v { font-size: 22px; font-weight: var(--fw-semibold); font-variant-numeric: tabular-nums; }
svg { width: 100%; display: block; margin-top: 6px; }
.band { fill: var(--c-ok); opacity: 0.12; }
.chart__axis { display: flex; justify-content: space-between; font-size: 12px; color: var(--c-text-3); }
.chart__empty { padding: 26px 0; text-align: center; color: var(--c-text-2); font-size: 14px; }
.chart__normal { display: flex; align-items: center; gap: 8px; margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--c-separator);
  font-size: var(--fs-sm); color: var(--c-text-2); font-variant-numeric: tabular-nums; }
</style>
