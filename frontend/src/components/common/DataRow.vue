<script setup lang="ts">
defineProps<{ columns?: string[] }>();
</script>
<template>
  <div class="data-row">
    <slot
      ><span v-for="column in columns" :key="column">{{ column }}</span></slot
    >
  </div>
</template>
<style scoped>
.data-row {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(120px, 1fr);
  align-items: center;
  min-height: 48px;
  border-bottom: 1px solid var(--color-border-default);
  padding: 0 12px;
  font-size: 14px;
  font-weight: 600;
}
.data-row:hover {
  background: var(--color-status-info-bg);
}
</style>
