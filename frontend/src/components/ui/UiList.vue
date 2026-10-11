<script setup>
// Bordered list of rows (UiListRow) with full-width dividers. `plain` is kept for older callers; it looks the same.
defineProps({ plain: Boolean });
</script>
<template>
  <div :class="['ui-list', { 'ui-list--plain': plain }]" role="list">
    <slot />
  </div>
</template>
<style>
/* not scoped: any row component placed in the list gets the divider */
.ui-list { background: var(--c-surface); border: 1px solid var(--c-border); border-radius: var(--radius-lg); overflow: hidden; }
.ui-list > * + * { border-top: 1px solid var(--c-separator); }
</style>
