<script setup lang="ts">
defineProps<{ title: string; description?: string }>();
</script>
<template>
  <header class="page-header">
    <div>
      <h1>{{ title }}</h1>
      <p v-if="description">{{ description }}</p>
    </div>
    <div class="page-header__actions"><slot /></div>
  </header>
</template>
<style scoped>
.page-header {
  display: flex;
  min-height: 68px;
  align-items: flex-start;
  justify-content: space-between;
  gap: 18px;
}
.page-header h1 {
  margin: 0;
  font-size: 26px;
  font-weight: 600;
  line-height: 32px;
}
.page-header p {
  margin: 4px 0 0;
  color: var(--color-text-muted);
  font-size: 13px;
}
.page-header__actions {
  display: flex;
  gap: 8px;
}
</style>
