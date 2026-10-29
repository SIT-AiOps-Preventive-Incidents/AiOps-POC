<script setup>
// The RadarOps crest: a hero's shield in two pastel facets, a dark visor across it with a scan line and the
// glowing "eye" that found something, radar arcs above like a crest, a small star below. Watchful, not cute.
import { useId } from "vue";
defineProps({ size: { type: Number, default: 30 } });
const id = useId();
</script>
<template>
  <svg :width="size" :height="size" viewBox="0 0 32 32" aria-hidden="true" class="ui-brand">
    <defs>
      <linearGradient :id="`${id}l`" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#c8f0de" /><stop offset="1" stop-color="#94dcbc" /></linearGradient>
      <linearGradient :id="`${id}r`" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#b7e3f7" /><stop offset="1" stop-color="#7cc2e6" /></linearGradient>
      <radialGradient :id="`${id}e`"><stop offset="0" stop-color="#ffffff" /><stop offset=".45" stop-color="#9ff0ff" /><stop offset="1" stop-color="#9ff0ff" stop-opacity="0" /></radialGradient>
    </defs>
    <!-- shield: left facet mint, right facet sky -->
    <path d="M16 1.8L4 6.4v8.4c0 7.6 5.2 12.8 12 15.4z" :fill="`url(#${id}l)`" />
    <path d="M16 1.8l12 4.6v8.4c0 7.6-5.2 12.8-12 15.4z" :fill="`url(#${id}r)`" />
    <!-- crest: two radar arcs -->
    <path d="M12.6 8.4a4.8 4.8 0 0 1 6.8 0" fill="none" stroke="#ffffff" stroke-width="1.3" stroke-linecap="round" opacity=".85" />
    <path d="M14.3 10.2a2.4 2.4 0 0 1 3.4 0" fill="none" stroke="#ffffff" stroke-width="1.3" stroke-linecap="round" opacity=".85" />
    <!-- visor -->
    <path d="M6.6 13.2h18.8l-1.7 4.6a2 2 0 0 1-1.9 1.3H10.2a2 2 0 0 1-1.9-1.3z" fill="#1b2636" />
    <path d="M9.4 16.2h13.2" stroke="#5fd3f2" stroke-width=".9" stroke-linecap="round" opacity=".55" />
    <circle cx="19.6" cy="16.2" r="3.4" :fill="`url(#${id}e)`" />
    <circle cx="19.6" cy="16.2" r="1.15" fill="#ffffff" />
    <!-- star -->
    <path d="M16 21.6l.8 1.7 1.8.3-1.3 1.3.3 1.8-1.6-.9-1.6.9.3-1.8-1.3-1.3 1.8-.3z" fill="#fdf6d8" />
  </svg>
</template>
<style scoped>
.ui-brand { flex: none; display: block; filter: drop-shadow(0 3px 8px rgba(124, 194, 230, 0.25)); }
</style>
