<script setup>
// A small drawn scene for the empty side of a card: the thing's glyph on a soft pastel disc, an orbit ring, and a
// badge that says what pressing the card does (+ connect, → open, ✓ healthy, ! look at it). It tells the action
// before the words do, so a row of cards reads as a row of doors.
import { computed, useId } from "vue";
import UiGlyph from "./UiGlyph.vue";
const props = defineProps({ glyph: { type: String, required: true }, hue: { type: String, default: "sky" },
  badge: { type: String, default: "arrow" }, size: { type: Number, default: 76 } });
const HUE = {
  sky: ["#acdcf3", "#3d7fa8"], mint: ["#a9e5c9", "#2f8a64"], lilac: ["#cbbcf4", "#6a52b8"], peach: ["#f9cba9", "#b9643a"],
  butter: ["#f6e29a", "#9a7a1e"], rose: ["#f5b6c2", "#b04a5f"], slate: ["#cdd4df", "#5d6a7e"],
};
const c = computed(() => HUE[props.hue] || HUE.sky);
const id = useId().replace(/[^a-zA-Z0-9_-]/g, "");
const seed = computed(() => [...props.glyph].reduce((a, ch) => (a * 17 + ch.charCodeAt(0)) % 911, 3));
</script>
<template>
  <span class="ui-spot" :style="{ width: `${size}px`, height: `${size}px` }" aria-hidden="true">
    <svg viewBox="0 0 80 80" class="ui-spot__bg">
      <defs><filter :id="`${id}r`" x="-15%" y="-15%" width="130%" height="130%">
        <feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" :seed="seed" result="n" />
        <feDisplacementMap in="SourceGraphic" in2="n" scale="4" xChannelSelector="R" yChannelSelector="G" /></filter></defs>
      <g :filter="`url(#${id}r)`">
        <!-- a painted blob, not a perfect disc -->
        <path d="M40 9c15 0 30 11 30 30 0 18-14 32-31 32-18 0-30-15-30-31C9 22 23 9 40 9z" :fill="c[0]" opacity=".34" />
        <!-- a loop sketched in one go, that does not quite close -->
        <path d="M17 26c6-12 21-19 35-14 14 5 22 20 17 34-4 14-19 24-34 21C21 64 10 50 12 36" fill="none" stroke="#b7aecb" stroke-opacity=".55"
              stroke-width="1.1" stroke-linecap="round" />
        <path d="M66 18l3-3M71 25l4-1M64 13l1-4" :stroke="c[0]" stroke-width="1.6" stroke-linecap="round" opacity=".8" />
      </g>
    </svg>
    <span class="ui-spot__g"><UiGlyph :name="glyph" :size="Math.round(size * 0.52)" /></span>
    <svg v-if="badge !== 'none'" viewBox="0 0 24 24" class="ui-spot__badge" :style="{ width: `${size * 0.32}px`, height: `${size * 0.32}px` }">
      <path d="M12 1.6c6 0 10.6 4.4 10.4 10.6-.2 5.8-4.8 10.2-10.6 10.2C6 22.4 1.5 17.8 1.7 11.8 1.9 6 6.2 1.6 12 1.6z" :fill="c[0]" />
      <path v-if="badge === 'plus'" d="M12 7.5v9M7.5 12h9" :stroke="c[1]" stroke-width="2.2" stroke-linecap="round" />
      <path v-else-if="badge === 'check'" d="M7.5 12.3l3 3 6-6.3" fill="none" :stroke="c[1]" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
      <g v-else-if="badge === 'alert'"><path d="M12 7v6" :stroke="c[1]" stroke-width="2.2" stroke-linecap="round" /><circle cx="12" cy="16.6" r="1.3" :fill="c[1]" /></g>
      <path v-else d="M8 12h8M12.8 8.6L16.2 12l-3.4 3.4" fill="none" :stroke="c[1]" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
  </span>
</template>
<style scoped>
.ui-spot { position: relative; display: grid; place-items: center; flex: none; }
.ui-spot__bg { position: absolute; inset: 0; width: 100%; height: 100%; }
.ui-spot__g { position: relative; transition: transform var(--dur) var(--ease); }
.ui-spot__badge { position: absolute; right: 6%; bottom: 6%; transition: transform var(--dur) var(--ease); }
/* the card around it lifts the scene a little on hover: the door opens */
:global(a:hover) > .ui-spot .ui-spot__g, :global(.spot-host:hover) .ui-spot__g { transform: translateY(-2px) scale(1.04); }
:global(a:hover) > .ui-spot .ui-spot__badge, :global(.spot-host:hover) .ui-spot__badge { transform: translate(2px, -1px); }
@media (prefers-reduced-motion: reduce) { .ui-spot__g, .ui-spot__badge { transition: none; } }
</style>
