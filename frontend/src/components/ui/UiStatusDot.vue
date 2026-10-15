<script setup>
// Shape as well as colour, matching UiPill: circle = ok / working, square = bad, triangle = warning, ring = no data.
defineProps({ tone: { type: String, default: "neutral" }, size: { type: Number, default: 9 } });
</script>
<template><span :class="['ui-dot', `ui-dot--${tone}`]" :style="{ width: `${size}px`, height: `${size}px` }" /></template>
<style scoped>
.ui-dot { display: inline-block; border-radius: 50%; flex: none; background: transparent; box-shadow: inset 0 0 0 1.5px var(--c-neutral); }
.ui-dot--ok { background: var(--c-ok); box-shadow: none; }
.ui-dot--bad { background: var(--c-bad); box-shadow: none; border-radius: 1px; }
.ui-dot--warn { background: var(--c-warn); box-shadow: none; border-radius: 0; clip-path: polygon(50% 0, 100% 100%, 0 100%); }
.ui-dot--ai { background: var(--c-ai); box-shadow: none; } .ui-dot--info { background: var(--c-info); box-shadow: none; }
</style>
