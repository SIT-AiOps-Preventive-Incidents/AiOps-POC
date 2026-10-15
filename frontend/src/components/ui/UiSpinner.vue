<script setup>
// Indeterminate loading, drawn as the same ring as UiProgressRing: the arc fills from empty to a full circle,
// then begins again - "the system is working on it". Blue = the system at work. Not a plain rotating dash.
defineProps({ size: { type: Number, default: 20 } });
</script>
<template>
  <span class="ui-spinner" role="progressbar" aria-label="Loading" :style="{ width: `${size}px`, height: `${size}px` }">
    <svg viewBox="0 0 50 50" aria-hidden="true">
      <circle class="track" cx="25" cy="25" r="20" />
      <circle class="bar" cx="25" cy="25" r="20" />
    </svg>
  </span>
</template>
<style scoped>
.ui-spinner { display: inline-block; flex: none; }
svg { width: 100%; height: 100%; transform-origin: center; animation: spinner-turn 2s linear infinite; }
.track { fill: none; stroke: var(--c-fill-2); stroke-width: 5; }
.bar { fill: none; stroke: var(--c-primary); stroke-width: 5; stroke-linecap: round;
  stroke-dasharray: 125.6; transform: rotate(-90deg); transform-origin: center;
  animation: spinner-fill 1.5s var(--ease, ease-in-out) infinite; }
@keyframes spinner-turn { to { transform: rotate(360deg); } }
/* 125.6 = 2*pi*20 (empty) -> 0 (full circle), then fade out and restart from empty */
@keyframes spinner-fill {
  0%   { stroke-dashoffset: 125.6; opacity: 0.45; }
  65%  { stroke-dashoffset: 0;     opacity: 1; }
  100% { stroke-dashoffset: 0;     opacity: 0; }
}
@media (prefers-reduced-motion: reduce) {
  svg { animation: none; }
  .bar { animation: none; stroke-dashoffset: 94; }   /* a static quarter-full arc */
}
</style>
