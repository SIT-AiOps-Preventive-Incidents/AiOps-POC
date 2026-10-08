<script setup>
defineProps({ tone: { type: String, default: "neutral" } }); // ok bad warn ai info neutral solid-bad solid-warn
</script>
<template><span :class="['ui-pill', `ui-pill--${tone}`]"><slot /></span></template>
<style scoped>
.ui-pill { display: inline-flex; align-items: center; gap: 5px; font-size: 12.5px; font-weight: var(--fw-semibold); padding: 3px 9px; border-radius: var(--radius-pill); white-space: nowrap; }
.ui-pill--neutral { background: var(--c-fill); color: var(--c-text-2); }
.ui-pill--ok { background: var(--c-ok-bg); color: var(--c-ok-text); }
.ui-pill--bad { background: var(--c-bad-bg); color: var(--c-bad-text); }
.ui-pill--warn { background: var(--c-warn-bg); color: var(--c-warn-text); }
.ui-pill--ai { background: var(--c-ai-bg); color: var(--c-ai-text); }
.ui-pill--info { background: var(--c-info-bg); color: var(--c-info-text); }
.ui-pill--solid-bad { background: var(--c-bad-text); color: #fff; }
.ui-pill--solid-warn { background: var(--c-warn); color: var(--c-text); }
</style>
