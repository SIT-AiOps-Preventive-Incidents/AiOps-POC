<script setup lang="ts">
defineProps<{ title?: string; flush?: boolean }>();
</script>
<template>
  <section class="panel" :class="{ 'panel--flush': flush }">
    <div v-if="title || $slots.header" class="panel__head">
      <h2 v-if="title">{{ title }}</h2>
      <slot name="header" />
    </div>
    <div class="panel__body"><slot /></div>
  </section>
</template>
<style scoped>
.panel {
  min-width: 0;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  padding: 16px;
}
.panel--flush {
  padding: 0;
  overflow: hidden;
}
.panel__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}
.panel__head h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  line-height: 26px;
}
.panel__body {
  min-width: 0;
}
.panel--flush .panel__head {
  padding: 16px 16px 0;
}
.panel--flush .panel__body {
  overflow: auto;
}
</style>
