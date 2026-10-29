<script setup>
// A placeholder block with a slow light sweep, shaped like the content that is about to land.
defineProps({ w: { type: String, default: "100%" }, h: { type: String, default: "14px" }, r: { type: String, default: "8px" } });
</script>
<template><span class="sk" :style="{ width: w, height: h, borderRadius: r }" aria-hidden="true" /></template>
<style scoped>
.sk { display: block; flex: none; position: relative; overflow: hidden; background: var(--c-fill); }
.sk::after { content: ""; position: absolute; inset: 0; transform: translateX(-100%);
  background: linear-gradient(90deg, transparent, color-mix(in srgb, var(--c-text) 7%, transparent), transparent); animation: sk 1.5s var(--ease) infinite; }
@keyframes sk { to { transform: translateX(100%); } }
@media (prefers-reduced-motion: reduce) { .sk::after { animation: none; } }
</style>
