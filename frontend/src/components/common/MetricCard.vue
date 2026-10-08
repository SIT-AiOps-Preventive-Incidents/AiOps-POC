<script setup lang="ts">
defineProps<{
  label: string;
  value: string | number;
  meta?: string;
  tone?: "default" | "danger" | "success";
}>();
</script>
<template>
  <article class="metric">
    <span>{{ label }}</span
    ><strong :class="tone">{{ value }}</strong
    ><small>{{ meta }}</small>
  </article>
</template>
<style scoped>
.metric {
  height: 112px;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: white;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.metric span,
.metric small {
  font-size: 12px;
  line-height: 18px;
}
.metric span {
  color: var(--color-text-muted);
}
.metric small {
  color: var(--color-text-dim);
}
.metric strong {
  font-size: 24px;
  line-height: 32px;
}
.metric strong.danger {
  color: var(--color-status-danger-text);
}
.metric strong.success {
  color: var(--color-status-success-text);
}
</style>
