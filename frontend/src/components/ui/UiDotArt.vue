<script setup>
// Halftone dot art for the edge of a card - generated, not an image, so it is crisp at any size and costs no request.
//   wave    a field of dots rolling like cloth, nearer rows bigger and brighter (action cards)
//   ribbon  nested squares twisting into depth, drawn as thin lines (the status card)
//   sphere  a dotted globe lit from one side (support / settings cards)
// Colour runs across the art from `from` to `to` (and `via`), and the whole thing fades out towards the text.
import { computed, useId } from "vue";
const props = defineProps({ variant: { type: String, default: "wave" }, from: { type: String, default: "#7c5cf6" },
  via: { type: String, default: "#4aa8f0" }, to: { type: String, default: "#f2a37a" }, seed: { type: Number, default: 1 },
  fade: { type: String, default: "left" } }); // which side fades into the card
const id = useId();
const W = 400, H = 260;

const wave = computed(() => {
  const dots = [], rows = 26, cols = 64;
  for (let r = 0; r < rows; r++) {
    const depth = r / (rows - 1);                       // 0 far .. 1 near
    const scale = 0.45 + depth * 0.75;
    for (let c = 0; c < cols; c++) {
      const u = c / (cols - 1);
      const x = W * (0.5 + (u - 0.5) * (0.6 + depth * 0.9));
      const h = Math.sin(u * 6.2 + r * 0.33 + props.seed) * 0.6 + Math.sin(u * 2.3 - r * 0.21 + props.seed * 2) * 0.4;
      const y = 40 + depth * 170 - h * (26 + depth * 30);
      if (x < -4 || x > W + 4) continue;
      dots.push({ x: x.toFixed(1), y: y.toFixed(1), r: (0.55 + depth * 1.05 * (0.6 + 0.4 * (h + 1) / 2)).toFixed(2),
        o: (0.18 + depth * 0.7).toFixed(2) });
    }
  }
  return dots;
});

const ribbon = computed(() => {
  const out = [], n = 34;
  for (let i = 0; i < n; i++) {
    const t = i / (n - 1);
    const s = 170 - t * 120, a = (t * 78 + props.seed * 9) * (Math.PI / 180);
    const cx = 230 + Math.sin(t * 3) * 30, cy = 140 + Math.cos(t * 2.4) * 18;
    const pts = [0, 1, 2, 3].map((k) => {
      const ang = a + (k * Math.PI) / 2;
      return `${(cx + Math.cos(ang) * s * 0.7).toFixed(1)},${(cy + Math.sin(ang) * s * 0.5).toFixed(1)}`;
    });
    out.push({ d: `M${pts.join(" L")} Z`, o: (0.12 + 0.5 * Math.sin(t * Math.PI)).toFixed(2) });
  }
  return out;
});

const sphere = computed(() => {
  const dots = [], n = 900, R = 118, cx = 250, cy = 150, golden = Math.PI * (3 - Math.sqrt(5));
  for (let i = 0; i < n; i++) {
    const y = 1 - (i / (n - 1)) * 2, rad = Math.sqrt(1 - y * y), th = golden * i + props.seed;
    const x = Math.cos(th) * rad, z = Math.sin(th) * rad;
    if (z < -0.15) continue;                               // only the side facing us
    const light = Math.max(0, x * -0.6 + y * -0.4 + z * 0.7);
    dots.push({ x: (cx + x * R).toFixed(1), y: (cy + y * R).toFixed(1), r: (0.5 + light * 1.4).toFixed(2), o: (0.15 + light * 0.75).toFixed(2) });
  }
  return dots;
});
const maskDir = computed(() => ({ left: "to right", right: "to left", top: "to bottom", none: null }[props.fade]));
</script>
<template>
  <svg class="ui-dotart" :viewBox="`0 0 ${W} ${H}`" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
    <defs>
      <linearGradient :id="`${id}g`" x1="0" x2="1" y1="0" y2="0.4">
        <stop offset="0" :stop-color="from" /><stop offset="0.55" :stop-color="via" /><stop offset="1" :stop-color="to" />
      </linearGradient>
      <linearGradient v-if="maskDir" :id="`${id}f`" :x1="fade === 'right' ? 1 : 0" :x2="fade === 'right' ? 0 : fade === 'top' ? 0 : 1"
                      y1="0" :y2="fade === 'top' ? 1 : 0">
        <stop offset="0" stop-color="#fff" stop-opacity="0" /><stop offset="0.45" stop-color="#fff" stop-opacity="1" />
      </linearGradient>
      <mask v-if="maskDir" :id="`${id}m`"><rect :width="W" :height="H" :fill="`url(#${id}f)`" /></mask>
    </defs>
    <g :mask="maskDir ? `url(#${id}m)` : undefined" :fill="`url(#${id}g)`" :stroke="variant === 'ribbon' ? `url(#${id}g)` : 'none'">
      <template v-if="variant === 'wave'"><circle v-for="(d, i) in wave" :key="i" :cx="d.x" :cy="d.y" :r="d.r" :opacity="d.o" /></template>
      <template v-else-if="variant === 'ribbon'"><path v-for="(p, i) in ribbon" :key="i" :d="p.d" fill="none" stroke-width="0.9" :opacity="p.o" /></template>
      <template v-else><circle v-for="(d, i) in sphere" :key="i" :cx="d.x" :cy="d.y" :r="d.r" :opacity="d.o" /></template>
    </g>
  </svg>
</template>
<style scoped>
.ui-dotart { position: absolute; pointer-events: none; display: block; }
</style>
