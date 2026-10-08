<script setup lang="ts">
withDefaults(
  defineProps<{
    tone?: "success" | "warning" | "danger" | "info" | "ai" | "neutral";
  }>(),
  { tone: "neutral" },
);
</script>

<template>
  <span class="badge" :class="`badge--${tone}`"><slot /></span>
</template>

<style scoped>
.badge {
  display: inline-flex;
  min-height: 26px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-sm);
  padding: 4px 12px;
  font-size: 11px;
  font-weight: 500;
  line-height: 16px;
  white-space: nowrap;
}
.badge--success {
  background: var(--color-status-success-bg);
  color: var(--color-status-success-text);
}
.badge--warning {
  background: var(--color-status-warning-bg);
  color: var(--color-status-warning-text);
}
.badge--danger {
  background: var(--color-status-danger-bg);
  color: var(--color-status-danger-text);
}
.badge--info {
  background: var(--color-status-info-bg);
  color: var(--color-status-info-text);
}
.badge--ai {
  background: var(--color-status-ai-bg);
  color: var(--color-status-ai-text);
}
.badge--neutral {
  background: var(--color-status-neutral-bg);
  color: var(--color-text-muted);
}
</style>
