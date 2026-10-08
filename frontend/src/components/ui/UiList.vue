<script setup>
// iOS inset grouped list. Rows are UiListRow; `plain` aligns separators to the left edge (rows without icons).
defineProps({ plain: Boolean });
</script>
<template>
  <div :class="['ui-list', { 'ui-list--plain': plain }]" role="list">
    <slot />
  </div>
</template>
<style scoped>
.ui-list { background: var(--c-surface); border-radius: var(--radius-lg); box-shadow: var(--shadow-1); overflow: hidden; }
.ui-list :deep(.ui-row + .ui-row)::before { content: ""; position: absolute; top: 0; left: 58px; right: 0; border-top: 0.5px solid var(--c-separator); }
.ui-list--plain :deep(.ui-row + .ui-row)::before { left: 16px; }
</style>
