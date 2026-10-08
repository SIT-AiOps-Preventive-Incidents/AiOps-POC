<script setup>
defineProps({ label: String, value: [String, Number], hint: String, tone: String });
</script>
<template>
  <div class="ui-kpi">
    <div class="ui-kpi__label">{{ label }}</div>
    <div :class="['ui-kpi__value', tone]">{{ value }}</div>
    <div v-if="hint" class="ui-kpi__hint">{{ hint }}</div>
  </div>
</template>
<style scoped>
.ui-kpi { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); padding: 14px 16px; min-width: 0; }
.ui-kpi__label { font-size: var(--fs-sm); color: var(--c-text-2); }
.ui-kpi__value { font-size: var(--fs-2xl); font-weight: var(--fw-bold); letter-spacing: -0.02em; margin-top: 2px; font-variant-numeric: tabular-nums; }
.ui-kpi__hint { font-size: 12px; color: var(--c-text-3); }
.bad { color: var(--c-bad-text); } .ok { color: var(--c-ok-text); }
</style>
