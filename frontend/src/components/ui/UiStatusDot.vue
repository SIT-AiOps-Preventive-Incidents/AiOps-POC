<script setup>
// A round dot with a faint halo; the colour is the status (green ok, amber watch, red broken, ring = no data).
defineProps({ tone: { type: String, default: "neutral" }, size: { type: Number, default: 9 } });
</script>
<template><span :class="['ui-dot', `ui-dot--${tone}`]" :style="{ width: `${size}px`, height: `${size}px` }" /></template>
<style scoped>
.ui-dot { display: inline-block; border-radius: 50%; flex: none; background: transparent; box-shadow: inset 0 0 0 1.5px var(--c-neutral); }
.ui-dot--ok { background: var(--c-ok); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-ok) 18%, transparent); }
.ui-dot--bad { background: var(--c-bad); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-bad) 18%, transparent); }
.ui-dot--warn { background: var(--c-warn); box-shadow: 0 0 0 3px color-mix(in srgb, var(--c-warn) 18%, transparent); }
.ui-dot--ai { background: var(--c-ai); box-shadow: none; } .ui-dot--info { background: var(--c-info); box-shadow: none; }
</style>
