<script setup>
defineProps({ tone: { type: String, default: "neutral" }, size: { type: Number, default: 9 } });
</script>
<template><span :class="['ui-dot', `ui-dot--${tone}`]" :style="{ width: `${size}px`, height: `${size}px` }" /></template>
<style scoped>
.ui-dot { display: inline-block; border-radius: 50%; flex: none; background: var(--c-neutral); }
.ui-dot--ok { background: var(--c-ok); } .ui-dot--bad { background: var(--c-bad); } .ui-dot--warn { background: var(--c-warn); }
.ui-dot--ai { background: var(--c-ai); } .ui-dot--info { background: var(--c-info); }
</style>
