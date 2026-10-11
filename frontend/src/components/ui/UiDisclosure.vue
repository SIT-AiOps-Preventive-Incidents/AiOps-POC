<script setup>
import UiIcon from "./UiIcon.vue";
defineProps({ title: String, meta: String, card: { type: Boolean, default: true } });
</script>
<template>
  <details :class="['ui-disc', { 'ui-disc--card': card }]">
    <summary><span>{{ title }} <span v-if="meta" class="muted">· {{ meta }}</span></span><UiIcon name="chevron_right" :size="16" class="chev" /></summary>
    <div class="ui-disc__body"><slot /></div>
  </details>
</template>
<style scoped>
.ui-disc > summary { list-style: none; cursor: pointer; display: flex; align-items: center; justify-content: space-between; gap: 10px; font-weight: var(--fw-semibold); }
.ui-disc > summary::-webkit-details-marker { display: none; }
.ui-disc--card { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); }
.ui-disc--card > summary { padding: 14px 18px; }
.ui-disc--card > summary:hover { background: var(--c-hover); }
.ui-disc--card .ui-disc__body { padding: 0 18px 16px; }
.ui-disc:not(.ui-disc--card) > summary { color: var(--c-primary); font-size: var(--fs-sm); font-weight: var(--fw-medium); justify-content: flex-start; }
.chev { color: var(--c-text-3); transition: transform var(--dur) var(--ease); }
.ui-disc[open] > summary .chev { transform: rotate(90deg); }
</style>
