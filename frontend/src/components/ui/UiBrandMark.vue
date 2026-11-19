<script setup>
// The RadarOps mark: a masked sentinel. A hero's domino mask in two lilac tones, two eyes glowing cyan behind it,
// inside a faint radar ring - the watcher that never looks away. Pastel, no outline, readable down to 16 px.
import { useId } from "vue";
defineProps({ size: { type: Number, default: 30 }, ring: { type: Boolean, default: true } });
const id = useId();
</script>
<template>
  <svg :width="size" :height="size" viewBox="0 0 64 64" aria-hidden="true" class="ui-brand">
    <defs><radialGradient :id="`${id}e`"><stop offset="0" stop-color="#ffffff" /><stop offset=".5" stop-color="#9ff0ff" /><stop offset="1" stop-color="#9ff0ff" stop-opacity="0" /></radialGradient></defs>
    <template v-if="ring">
      <circle cx="32" cy="32" r="29" fill="#cbbcf4" opacity=".22" />
      <circle cx="32" cy="32" r="21" fill="none" stroke="#cbbcf4" stroke-width="1.6" opacity=".6" />
    </template>
    <path d="M5 28c8-6.5 18.5-6.5 27 0 8.5-6.5 19-6.5 27 0-1 9.5-7.4 14.6-14.6 14.6-5.2 0-9.4-3-12.4-6.3-3 3.3-7.2 6.3-12.4 6.3C12.4 42.6 6 37.5 5 28z" fill="#8f7fe0" />
    <path d="M5 28c8-6.5 18.5-6.5 27 0 8.5-6.5 19-6.5 27 0-2 2.2-4.2 3.2-6.4 3.2-6.2-3.2-14.4-3.2-20.6 2-6.2-5.2-14.4-5.2-20.6-2-2.2 0-4.4-1-6.4-3.2z" fill="#b8a9f2" />
    <ellipse cx="19.5" cy="33.2" rx="6.4" ry="3.8" fill="#1b2636" /><ellipse cx="44.5" cy="33.2" rx="6.4" ry="3.8" fill="#1b2636" />
    <circle cx="20.6" cy="33.2" r="4.6" :fill="`url(#${id}e)`" /><circle cx="45.6" cy="33.2" r="4.6" :fill="`url(#${id}e)`" />
    <circle cx="20.6" cy="33.2" r="1.5" fill="#fff" /><circle cx="45.6" cy="33.2" r="1.5" fill="#fff" />
  </svg>
</template>
<style scoped>
.ui-brand { flex: none; display: block; filter: drop-shadow(0 3px 10px rgba(143, 127, 224, 0.35)); }
</style>
